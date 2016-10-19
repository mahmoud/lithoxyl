
import os
import time
import sqlite3
import threading
from json import JSONEncoder
from collections import deque, defaultdict, Mapping, Iterable, Sized


DEFAULT_INTERVAL = 200  # milliseconds
DEFAULT_RING_SIZE = 1000

CREATE_QTMPL = 'CREATE TABLE IF NOT EXISTS {table_name} ({cols})'
INSERT_QTMPL = 'INSERT INTO {table_name} ({cols}) VALUES ({qmarks})'
TABLE_INFO_QTMPL = 'PRAGMA table_info({table_name})'
TRIG_QTMPL = """CREATE TRIGGER {trig_name}
AFTER INSERT ON {table_name}
BEGIN
  DELETE FROM {table_name} WHERE id <= NEW.id - {size};
END"""

# would do IF EXISTS, but older sqlites didn't have it
DROP_TRIG_QTMPL = 'DROP TRIGGER {trig_name}'


class IntervalThreadActor(object):
    """Manages a thread that calls a `process` function and waits
    `interval` milliseconds before calling the function again.

    Args:
      process (callable): Function to call periodically. Takes no arguments.
      interval (number): Milliseconds to wait before next call of `process`.

    """
    def __init__(self, process, interval=None, **kwargs):
        self.process = process

        self._thread = None
        self._stopping = threading.Event()
        self._pid = None

        if interval is None:
            interval = DEFAULT_INTERVAL
        self.interval = self._orig_interval = float(interval)
        max_interval = kwargs.pop('max_interval', None)
        self.max_interval = float(max_interval or interval * 8)
        self._daemonize_thread = kwargs.pop('daemonize_thread', True)
        if kwargs:
            raise TypeError('unexpected keyword arguments: %r' % kwargs.keys())

        self._run_start_time = 0
        self._process_call_time = 0
        self._process_call_count = 0

    def get_stats(self):
        ret = {'run_start_time': self._run_start_time,
               'process_call_time': self._process_call_time,
               'process_call_count': self._process_call_count}
        return ret

    def is_alive(self):
        return self._thread and self._thread.is_alive()

    def start(self):
        if self.is_alive():
            return
        # os.getpid compare allows restarting after forks
        if os.getpid() == self._pid and self._stopping.is_set():
            # alive and stopping
            raise RuntimeError('expected caller to wait on join'
                               ' before calling start again')
        self._pid = os.getpid()
        self._stopping.clear()
        self._thread = threading.Thread(target=self._run)
        self._thread.daemon = self._daemonize_thread
        self._thread.start()
        return

    def stop(self):
        "actually, 'start_stopping' is more accurate"
        # TODO: what if we fork and the _run hasn't finished stopping,
        # so stopping is still set, but the thread is not alive. need
        # to reset the stopping state, or raise an error because the
        # data might not be clean.
        if self.is_alive():
            self._stopping.set()
        else:
            self._stopping.clear()
        return

    def join(self, timeout=None):
        if not self._thread:
            raise RuntimeError('actor must be started before it can be joined')
        self._thread.join(timeout=timeout)
        ret = self.is_alive()
        if not ret:
            self._stopping.clear()
        return ret

    def log(self, level, name, message):
        pass  # print level, '-', name, '-', message

    def _run(self):
        self._run_start_time = time.time()
        # TODO: start delay/jitter?
        try:
            while not self._stopping.is_set():
                self._process_call_count += 1
                cur_start_time = time.time()
                try:
                    self.process()
                except SystemExit:
                    pass  # presumably bc daemon
                except Exception as e:
                    self.log('critical', 'process_exception',
                             '%s - process() raised: %r' % (time.time(), e))
                    self.interval = min(self.interval * 2, self.max_interval)
                else:
                    decrement = (self.max_interval - self._orig_interval) / 8
                    self.interval = max(self.interval - decrement,
                                        self._orig_interval)
                cur_duration = time.time() - cur_start_time
                self._process_call_time += cur_duration
                interval_seconds = self.interval / 1000.0
                self._stopping.wait(interval_seconds)
        finally:
            self._stopping.clear()
        return


class SQLiteRingleader(object):
    def __init__(self, file_path, **kwargs):
        self.file_path = file_path

        self.default_ring_size = kwargs.pop('default_size', DEFAULT_RING_SIZE)

        # autodisable ignores db initialization failures, effectively
        # disarming managed rings
        self.autodisable = kwargs.pop('autodisable', False)

        self._enable_wal = kwargs.pop('wal', True)
        self._interval = kwargs.pop('flush_interval', DEFAULT_INTERVAL)
        self._max_interval = kwargs.pop('max_flush_interval', None)
        autostart = kwargs.pop('autostart', True)
        if kwargs:
            raise TypeError('unexpected keyword arguments: %r' % kwargs.keys())

        self._actor = None
        self.ring_map = {}
        if autostart:
            self.start()
        return

    def get_stats(self, name):
        ret = {}
        ring = self.ring_map[name]
        ret.update(ring.get_stats())

        if self._actor:
            ret['ring_actor'] = self._actor.get_stats()
        return ret

    def is_alive(self):
        try:
            return self._actor.is_alive()
        except Exception:
            return False

    def start(self):
        if not self._actor:
            self._actor = IntervalThreadActor(self.flush,
                                              interval=self._interval,
                                              max_interval=self._max_interval)
        self._actor.start()

    def stop(self):
        """Stop flushing all rings to disk. Tells the internal thread actor to
        gracefully finish its current batch and stop its thread when
        complete.
        """
        if self._actor:
            return self._actor.stop()
        return

    def join(self, timeout=None):
        if not self._actor:
            raise RuntimeError('must be started before join')
        self._actor.join(timeout=timeout)

    def register(self, name, fields, **kwargs):
        # TODO: note changing the name for versioning
        serialize = kwargs.pop('serialize', None)
        if serialize and not callable(serialize):
            raise TypeError('expected serialize to be callable, not %r'
                            % serialize)
        if kwargs:
            raise TypeError('unexpected keyword arguments: %r' % kwargs.keys())

        # TODO: behavior if already exists
        ring = SQLiteRing(file_path=self.file_path,
                          table_name=name,
                          fields=fields,
                          serialize=serialize,
                          size=self.default_ring_size,
                          wal=self._enable_wal,
                          autoinit=False,
                          standalone=False)
        try:
            ring.init_db()
        except Exception:
            if not self.autodisable:
                raise
            # TODO: log

        self.ring_map[name] = ring
        return ring

    def flush(self, name=None):
        if name:
            return self.ring_map[name].flush()

        for ring in self.ring_map.values():
            try:
                ring.flush()
            except Exception:
                pass  # TODO
        return

    def __getitem__(self, key):
        if self._actor:
            self._actor.start()  # kick the actor in case there's been a fork
        try:
            return self.ring_map[key]
        except KeyError:
            raise KeyError(key)  # call SQLiteRingleader.register first


class SQLiteRing(object):
    _default_sql_type = 'TEXT'
    _trig_suffix = '_trim'

    # TODO: option to recreate table if exists

    def __init__(self, file_path, table_name, fields, **kwargs):
        self.file_path = file_path
        self.table_name = table_name
        self.trigger_name = self.table_name + self._trig_suffix
        self.fields = tuple(fields)

        self.size = int(kwargs.pop('size', DEFAULT_RING_SIZE))
        if not self.size > 0:
            raise ValueError('expected ring size greater than 0, not %r'
                             % self.size)
        self.queue_size = int(kwargs.pop('queue_size', self.size))
        if not self.queue_size > 0:
            raise ValueError('expected queue size greater than 0, not %r'
                             % self.queue_size)

        self._enable_wal = kwargs.pop('wal', True)
        autoinit = kwargs.pop('autoinit', True)
        self._table_created = False
        autostart = kwargs.pop('autostart', True) and autoinit  # see exc below
        self.standalone = kwargs.pop('standalone', True)
        self._interval = kwargs.pop('flush_interval', DEFAULT_INTERVAL)
        self._max_interval = kwargs.pop('max_flush_interval', None)
        self.serialize = kwargs.pop('serialize', None)
        if self.serialize and not callable(self.serialize):
            raise TypeError('expected serialize to be callable, not %r'
                            % self.serialize)
        if kwargs:
            raise TypeError('unexpected keyword arguments: %r' % kwargs.keys())
        self._actor = None

        self._init_table_queries()
        self.resize_ring(size=self.size, queue_size=self.queue_size)

        self.last_logs = defaultdict(lambda: deque(maxlen=10))
        self._flush_call_time = 0
        self._flush_call_count = 0
        self._flush_record_count = 0
        self._db_init_time = 0

        if autoinit:
            self.init_db()
        if autostart and self.standalone:
            if not autoinit:
                raise ValueError('cannot autostart without autoinitializing '
                                 ' db. remove autostart or use autoinit=True.')
            self.start()
        return

    @property
    def field_names(self):
        cols = getattr(self, '_cols', None)
        if not cols:
            return []
        return [name for name, type in cols]

    def get_stats(self):
        ret = {'flush_call_time': self._flush_call_time,
               'flush_call_count': self._flush_call_count,
               'flush_record_count': self._flush_record_count}
        if self._actor:
            ret['ring_actor'] = self._actor.get_stats()
        try:
            ret['db_file_size'] = os.path.getsize(self.file_path)
        except OSError:
            ret['db_file_size'] = -1
        return ret

    def is_alive(self):
        try:
            return self._actor.is_alive()
        except Exception:
            return False

    def start(self):
        if not self.standalone:
            raise RuntimeError('not in standalone mode, start from leader,'
                               ' or set/pass standalone=False.')
        if not self._actor:
            self._actor = IntervalThreadActor(self.flush,
                                              interval=self._interval,
                                              max_interval=self._max_interval)
        self._actor.start()

    def stop(self):
        """Stop flushing all rings to disk. Tells the internal thread actor to
        gracefully finish its current batch and stop its thread when
        complete.
        """
        if self._actor:
            return self._actor.stop()
        return

    def join(self, timeout=None):
        if not self.standalone:
            raise RuntimeError('not in standalone mode, join from leader')
        if not self._actor:
            raise RuntimeError('must be started before join')
        self._actor.join(timeout=timeout)

    def _init_table_queries(self):
        self._cols = cols = [('id', 'INTEGER PRIMARY KEY AUTOINCREMENT')]
        for field in self.fields:
            if isinstance(field, basestring):
                col_name, col_type = field, self._default_sql_type
            else:
                try:
                    col_name, col_type = field
                    col_type = col_type.upper()  # sqlite type as a string
                except Exception:
                    raise TypeError('expected valid field (string or tuple),'
                                    ' not %r' % (field,))
            cols.append((col_name, col_type))

        cols_types_str = ', '.join(['%s %s' % (cn, ct) for cn, ct in cols])
        self._create_q = CREATE_QTMPL.format(table_name=self.table_name,
                                             cols=cols_types_str)
        # no id column for the insert query
        cols = cols[1:]
        cols_str = ', '.join([cn for cn, _ in cols])
        qmarks_str = ', '.join('?' * len(cols))
        self._insert_q = INSERT_QTMPL.format(table_name=self.table_name,
                                             cols=cols_str,
                                             qmarks=qmarks_str)
        return

    def _get_conn(self):
        return sqlite3.connect(self.file_path)

    def init_db(self):
        # create db and set journal mode
        conn = self._get_conn()
        if self._enable_wal:
            conn.execute('PRAGMA journal_mode=wal')

        self._create_table()
        self.resize_ring()
        self._db_init_time = time.time()
        return

    def resize_ring(self, size=None, queue_size=None):
        """Resize ring sets and potentially updates the size of the
        ring. Depending on the presence of *size* and *queue_size*,
        `resize_ring` creates/recreates the triggers in the database,
        as well as resizes the in-memory queue.

        This method is safe to call before the ring is active, but
        there are no guarantees with online resizing, especially with
        multiple worker processes. In specific cases the change may be
        reverted, or a small amount of data might be written
        twice. That said, practically, this method will not crash
        your application or corrupt your database file.
        """
        # recreating the trigger to allow seamless resizes of ring
        if size is None:
            size = self.size
        else:
            self.size = size

        if queue_size is not None:
            self.queue = deque(getattr(self, 'queue', ()), maxlen=queue_size)

        self._trig_q = TRIG_QTMPL.format(trig_name=self.trigger_name,
                                         table_name=self.table_name,
                                         size=self.size)
        self._drop_trig_q = DROP_TRIG_QTMPL.format(trig_name=self.trigger_name)

        if self._table_created:
            with self._get_conn() as conn:
                # this is necessary because CREATE TRIGGER IF NOT EXISTS
                # is more recent than some Python 2.7 releases.
                try:
                    conn.execute(self._drop_trig_q)
                except sqlite3.OperationalError as oe:
                    pass
                try:
                    conn.execute(self._trig_q)
                except sqlite3.OperationalError as oe:
                    pass
        return

    def _create_table(self, **kwargs):
        verify = kwargs.pop('verify', True)
        if kwargs:
            raise TypeError('unexpected keyword arguments: %r' % kwargs.keys())
        with self._get_conn() as conn:
            conn.execute(self._create_q)
        if not verify:
            return

        table_fail = '%s while creating table with ' + repr(self._create_q)

        advice = ('Check the database schema (%s) or remove it and try again.'
                  % self.file_path)
        table_fail += '. ' + advice

        with self._get_conn() as conn:
            tinfo_q = TABLE_INFO_QTMPL.format(table_name=self.table_name)
            cursor = conn.execute(tinfo_q)
            cols = cursor.fetchall()
            if len(cols) != len(self._cols):
                raise RuntimeError(table_fail % 'Field count mismatch')
            for i, col in enumerate(cols):
                col_name, col_type = col[1], col[2]

                if col_name != self._cols[i][0]:
                    msg = ('Column %s field name mismatch (%s vs %s)'
                           % (i, col_name, self._cols[i][0]))
                    raise RuntimeError(table_fail % msg)
                if col_type != self._cols[i][1].split()[0]:
                    msg = ('Column %s field type mismatch (%s vs %s)'
                           % (i, col_type, self._cols[i][1].split()[0]))
                    raise RuntimeError(table_fail % msg)
        self._table_created = True
        return

    def log(self, level, name, message):
        # setattr(self, '_log_i', getattr(self, '_log_i', 0) + 1)
        # if not self._log_i % 100:
        #     print level, '-', name, '-', message
        # print level, '-', name, '-', message
        self.last_logs[name].append(message)
        return

    def _log_record_drop(self, op, record, exception):
        try:
            rec_repr = repr(record)
        except Exception:
            rec_repr = object.__repr__(record)
        self.log('critical', 'record_drop',
                 '%s got %r, dropping record %s' % (op, exception, rec_repr))
        return

    def flush(self):
        # corner case handled: get an exception while writing a record.
        # what to do? could be a DB failure, could be a problem with the record
        # Non-sqlite exceptions have no special handling
        if not self._db_init_time:
            raise RuntimeError('called .flush() without initializing db.'
                               ' use autoinit=True or call .init_db()')

        self._flush_call_count += 1
        fcc, queue = self._flush_call_count, self.queue

        self.log('info', 'flush_call', '#%s - %s records in queue'
                 % (fcc, len(queue)))
        if len(queue) == 0:
            return
        count, stime, insert_q = 0, time.time(), self._insert_q

        with self._get_conn() as conn:
            while 1:
                try:
                    rec = queue.popleft()
                except IndexError:
                    break
                if self.serialize:
                    try:
                        rec = self.serialize(rec)
                    except Exception as e:
                        self._log_record_drop('serialize', rec, e)
                        continue

                try:
                    conn.execute(insert_q, rec)
                    count += 1
                except sqlite3.OperationalError:
                    # This block re-enqueues the current unprocessed record
                    # for retry. OperationalErrors include disk fullness, etc.
                    if len(queue) < self.size:
                        self.queue.appendleft(rec)
                    raise
                except sqlite3.Error as e:
                    # all other sql exceptions cause the record to drop
                    self._log_record_drop('insert', rec, e)
                    continue

        cur_dur = time.time() - stime
        self._flush_call_time += cur_dur
        self._flush_record_count += count
        self.log('info', 'flush_done', '#%s - wrote %s records in %s ms'
                 % (fcc, count, round(cur_dur * 1000.0, 2)))
        return

    def append(self, record):
        if not len(record) == len(self.fields):
            raise ValueError('expected record of length %r' % len(self.fields))
        self.queue.append(record)

    def raw_query(self, query, params=()):
        with self._get_conn() as conn:
            rows = conn.execute(query, params).fetchall()
        return rows


class RobustJSONEncoder(JSONEncoder):
    def __init__(self, **kw):
        kw.setdefault('skipkeys', True)
        kw.setdefault('ensure_ascii', True)
        kw.setdefault('sort_keys', True)
        super(RobustJSONEncoder, self).__init__(**kw)

    def default(self, obj):
        if isinstance(obj, Mapping):
            try:
                return dict(obj)
            except:
                pass
        if isinstance(obj, Sized) and isinstance(obj, Iterable):
            return list(obj)
        if callable(getattr(obj, 'to_dict', None)):
            return obj.to_dict()

        return repr(obj)


_robust_json_encoder = RobustJSONEncoder()


def robust_json_encode(obj):
    return _robust_json_encoder.encode(obj)


def main_single():
    ring = SQLiteRing('ring.db', 'ring', ['payload', ('payload_2', 'integer')])

    rounds = 3000
    for x in xrange(rounds):
        ring.append(('test', 1))
        if 1500 < ring._flush_record_count < 2000 and ring.is_alive():
            print('stopping')
            ring.stop()
        time.sleep(0.001)  # make some time

    from pprint import pprint
    last_logs = dict([(k, list(v)) for k, v in ring.last_logs.items()])
    pprint(last_logs)

    records = ring.raw_query('SELECT * FROM ' + ring.table_name)
    print(len(records), 'records in the database')


def main_leader():
    ringleader = SQLiteRingleader('leader.db')
    ringleader.register('test', ['payload', ('payload_2', 'integer')])

    start_time = time.time()
    rounds = 3000
    ring = ringleader['test']
    for x in xrange(rounds):
        ring.append(('test', 1))
        if x == 2000:
            total_time = time.time() - start_time
            print('stopping')
            ringleader.stop()
        time.sleep(0.001)  # make some time

    from pprint import pprint
    last_logs = dict([(k, list(v)) for k, v in ring.last_logs.items()])
    pprint(last_logs)

    records = ring.raw_query('SELECT * FROM ' + ring.table_name)
    print(len(records), 'records in the database')
    print('%s flushes for %s records in %s seconds of %s seconds total'
          % (ring._flush_call_count, ring._flush_record_count,
             round(ring._flush_call_time, 5), total_time))
    pprint(ringleader.get_stats('test'))
    return


def main_thread_test():
    x = [0]

    def target():
        print('hiya', x[0])
        x[0] += 1

    ta = IntervalThreadActor(target, daemonize_thread=False)
    ta.start()
    ta.stop()
    ta.join(1)
    ta.start()
    time.sleep(2)
    ta.stop()


main = main_leader


if __name__ == '__main__':
    main()


# NOTES
"""Fields:
Time, Message Type, CAL type, CAL name, status, data, duration, thread_id, process_id
ctx.recent['cal'].append((msg_type.__name__, cal_type,
                          name, status, data, duration, thread_id))

# Having a "WHEN" filter on the trigger didn't really speed things up
# at realistic production/flushing rates. Here's an example for
# safekeeping: WHEN NEW.id % 1500 = 0


# executemany - not actually faster for simulated data. may be faster
# for a more organic example, but still doesn't offer fine-grained
# error handling

# metadata table with pid/last time written/number of records written
# faster than count(*)? max(row_id) - min(row_id) (depends on whether we use times)

# Scratched the idea of doing timestamp-based filtering of inputs.

# Caveat: Be wary of mutliprocess SQLite access on NFS. the fcntl is
# often broken, and it's probably just better to avoid it altogether.

# Daemon threads

threading._limbo is threads that are starting. threading.enumerate()
iterates over starting and started threads. Not including the
MainThread. The MainThread is _this_ thread, not really a newly started
thread. It represents the current thread.

threading._shutdown is waited on in pythonrun.c. It iterates over all
running threads (as given by threading.enumerate) and joins on each
one in an arbitrary order (threading._pickSomeNonDaemonThread).

All non-daemon threads must shut down before sys.atexit is called. So
you can implement your own waiting/joining on *daemon* threads in
sys.atexit.

No real way to wait on multiple events with threads (without creating
a thread per event).

# Not used but code to introspect triggers, etc.:
SELECT * FROM sqlite_master WHERE type="trigger" and name=? and tbl_name=?

"""
