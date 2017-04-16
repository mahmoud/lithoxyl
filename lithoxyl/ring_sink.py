import os
import thread
import json

import ring


class RingSink(object):
    def __init__(self, db_path, name='structured_log'):
        self.ring = ring.SQLiteRing(db_path, name, SCHEMA, size=int(1e6))

    def on_begin(self, event):
        self.insert('begin', event)

    def on_warn(self, event):
        self.insert('warn', event)

    def on_end(self, event):
        self.insert('end', event)

    def on_comment(self, event):
        self.insert('comment', event)

    def insert(self, type_, event):
        self.ring.start()
        if event.action.parent_action:
            parent_id = event.action.parent_action.action_id
        else:
            parent_id = None
        try:
            exc_trace = event.action.exc_event.exc_info.get_formatted()
        except Exception:
            exc_trace = None
        self.ring.append((
            os.getpid(),  # process_id
            thread.get_ident(),
            event.action.logger.name,  # logger_name
            type_,  # type
            event.action.name,  # name
            event.status_char,  # status
            event.level_name,  # level
            event.action_id,  # action_id
            parent_id,  # parent_action_id
            json.dumps(event.action.data_map, sort_keys=True),  # payload
            exc_trace,  # exc_trace
            event.action.begin_event.etime,  # timestamp
            event.action.duration * 1e3,  # duration_ms
            ))


SCHEMA = [
    ('process_id', 'integer'),
    ('thread_id', 'integer'),
    'logger_name',
    'type',
    'name',
    'status',
    'level',
    ('action_id', 'integer'),
    ('parent_action_id', 'integer'),
    'payload',
    'exc_trace',
    ('timestamp', 'real'),
    ('duration_ms', 'real')
]



def _test():
    import lithoxyl
    import time

    import tempfile
    import sqlite3
    import time
    import shutil

    path = tempfile.mkdtemp() + '/test.db'
    #path = 'test.db'
    rs = RingSink(path)
    tl = lithoxyl.Logger('test_logger')
    tl.add_sink(rs)

    class SpecificError(Exception): pass

    @tl.wrap(level='critical')
    def foo():
        with tl.critical('test_context'):
            time.sleep(0.1)
            tl.critical('test_leaf', extra1='cat', extra2=2).success()
            try:
                with tl.critical('exception'):
                    raise SpecificError('kablam')
            except SpecificError:  # don't want to mask real issues
                pass

    time.sleep(0.5)  # give ring a chance to flush

    foo()
    foo()

    result = sqlite3.connect(path).cursor().execute('SELECT * FROM structured_log').fetchall()

    #rs.ring.join()
    shutil.rmtree(path.rpartition('/')[0])

    return result

