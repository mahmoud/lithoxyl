# -*- coding: utf-8 -*-

import sys
import json
import time
import bisect
from collections import deque

from formatters import Formatter
from emitters import StreamEmitter
from quantile import QuantileAccumulator, P2QuantileAccumulator


class AggSink(object):
    "A 'dummy' sink that just aggregates the messages."
    def __init__(self):
        self.records = []

    def on_begin(self, record):
        pass

    def on_complete(self, record):
        self.records.append(record)


_MSG_ATTRS = ('name', 'level_name', 'status', 'message',
              'begin_time', 'end_time', 'duration')


class StructuredFileSink(object):
    def __init__(self, fileobj=None):
        self.fileobj = fileobj or sys.stdout

    def on_complete(self, record):
        msg_data = dict(record.extras)
        for attr in _MSG_ATTRS:
            msg_data[attr] = getattr(record, attr, None)
        json_str = json.dumps(msg_data, sort_keys=True)
        self.fileobj.write(json_str)
        self.fileobj.write('\n')


class RateAccumulator(object):
    """\
    The RateAccumulator provides basic accounting and rate estimation
    capabilities based on a single stream of timestamps. Note that the stream
    is assumed to be in order.
    """
    def __init__(self, sample_size=128):
        self.times = deque(maxlen=sample_size)
        self.total_count = 0
        self.creation_time = time.time()

    @property
    def sample_size(self):
        return self.times.maxlen

    def add(self, timestamp):
        """
        Adds a timestamp to the accumulator. Note that timestamps are
        expected to be added _in order_.
        """
        self.total_count += 1
        self.times.append(timestamp)

    def get_norm_times(self, ndigits=4):
        """\
        Mostly for debugging: returns the current reservoir of
        timestamps normalized to the first.
        """
        if not self.times:
            return []
        first = self.times[0]
        return [round(x - first, ndigits) for x in self.times]

    def get_rate(self, start_time=None, end_time=None):
        """\ Returns the per-second rate of the accumulator, taking into
        account the window designated by start_time and
        end_time.

        start_time defaults to the creation time of the
        accumulator. end_time defaults to current time.

        Note that if the window extends beyond the time range
        currently tracked by the reservoir, but less than the total
        lifespan of the accumulator, the rate will be an estimate.
        """
        if not self.times:
            return 0.0
        end_time = end_time or time.time()
        start_time = start_time or self.creation_time
        if start_time <= self.creation_time:
            count = self.total_count
        else:
            target_idx = bisect.bisect_left(self.times, start_time)
            count = len(self.times) - target_idx
            if not count:
                # if our reservoir has nothing to offer, i.e., the
                # rate is high enough to have lost all real datapoints
                # for the window described, we just return the current
                # rate of everything in the reservoir.
                count = len(self.times)
                start_time, end_time = self.times[0], self.times[-1]
            elif not target_idx:
                start_time = self.times[0]
        return count / (end_time - start_time)

    def __repr__(self):
        cn = self.__class__.__name__
        rate = self.get_rate()
        return '<%s rate=%.4f count=%r>' % (cn, rate, self.total_count)


class RateSink(object):
    """\
    The RateSink provides basic accounting and rate estimation
    facilities records as they pass through the system.

    It uses a reservoir system for predictable and stable memory
    use. See RateAccumulator for more information.

    A RateSink can be shared across multiple loggers.
    """
    def __init__(self, sample_size=128, getter=None):
        if getter is None:
            getter = lambda record: record.end_time
        self.getter = getter
        self.acc_map = {}
        self.sample_size = sample_size
        self.creation_time = time.time()

    def on_complete(self, record):
        name_time_map = self.acc_map.setdefault(record.logger, {})
        status_time_map = name_time_map.setdefault(record.name, {})
        try:
            acc = status_time_map[record.status]
        except:
            acc = RateAccumulator(sample_size=self.sample_size)
            status_time_map[record.status] = acc
        acc.add(record.end_time)

    def get_rates(self, max_time=None, **kw):
        """\
        Gets a dictionary of rates, grouped by logger and
        status. Aggregates are put under the special key,
        '__all__'. All rates are in terms of seconds.

        The caller can specify `start_time` and `end_time`, or use the
        convenience parameter `max_time`, which specifies how long
        before the current time the window should extend.
        """
        end_time = kw.pop('end_time', time.time())
        start_time = kw.pop('start_time', self.creation_time)
        if max_time:
            start_time = end_time - max_time

        ret = {}
        all_loggers_rate = 0.0
        for logger, name_map in self.acc_map.items():
            cur_logger_rate = 0.0
            ret[logger.name] = {}
            for name, status_map in name_map.items():
                cur_name_rate = 0.0
                ret[logger.name][name] = {}
                for status, acc in status_map.items():
                    cur_rate = acc.get_rate(start_time=start_time,
                                            end_time=end_time)
                    ret[logger.name][name][status] = cur_rate
                    cur_name_rate += cur_rate
                    cur_logger_rate += cur_rate
                    all_loggers_rate += cur_rate
                ret[logger.name][name]['__all__'] = cur_name_rate
            ret[logger.name]['__all__'] = cur_logger_rate
        ret['__all__'] = all_loggers_rate
        return ret

    def get_total_counts(self):
        """\
        Gets a dictionary of counts, grouped by logger and
        status. Aggregates are put under the special key,
        '__all__'. All counts are for the full lifetime of the sink.
        """
        ret = {}
        all_loggers_count = 0
        for logger, name_map in self.acc_map.items():
            cur_logger_count = 0
            ret[logger.name] = {}
            for name, status_map in name_map.items():
                cur_name_count = 0
                ret[logger.name][name] = {}
                for status, acc in status_map.items():
                    cur_count = acc.total_count
                    ret[logger.name][name][status] = cur_count
                    cur_name_count += cur_count
                    cur_logger_count += cur_count
                    all_loggers_count += cur_count
                ret[logger.name][name]['__all__'] = cur_name_count
            ret[logger.name]['__all__'] = cur_logger_count
        ret['__all__'] = all_loggers_count
        return ret

    def __repr__(self):
        cn = self.__class__.__name__
        total_rate_all = self.get_rates()['__all__']
        total_count_all = self.get_total_counts()['__all__']
        return '<%s total_rate=%.4f total_count=%r>' % (cn,
                                                        total_rate_all,
                                                        total_count_all)


from ewma import EWMAAccumulator, DEFAULT_PERIODS, DEFAULT_INTERVAL


class EWMASink(object):
    accumulator_type = EWMAAccumulator

    def __init__(self,
                 periods=DEFAULT_PERIODS,
                 interval=DEFAULT_INTERVAL,
                 getter=None):
        if getter is None:
            getter = lambda record: record.duration
        self.periods = periods
        self.interval = interval
        self.getter = getter
        self.acc_map = {}

    def on_complete(self, record):
        name_time_map = self.acc_map.setdefault(record.logger.name, {})
        status_time_map = name_time_map.setdefault(record.name, {})
        try:
            acc = status_time_map[record.status]
        except:
            acc = self.accumulator_type(periods=self.periods,
                                        interval=self.interval)
            status_time_map[record.status] = acc
        value = self.getter(record)
        acc.add(value)

    @staticmethod
    def _update_add(target, other):
        for k, v in other.iteritems():
            if v is None:
                continue
            try:
                target[k] += v
            except KeyError:
                target[k] = v
        return

    def get_values(self):
        ret = {}
        _update_add = self._update_add
        all_loggers_vals = ret['__all__'] = {}
        for logger, name_map in self.acc_map.items():
            ret[logger] = {}
            cur_logger_vals = ret[logger]['__all__'] = {}
            for name, status_map in name_map.items():
                ret[logger][name] = {}
                cur_name_vals = ret[logger][name]['__all__'] = {}
                for status, acc in status_map.items():
                    cur_vals = acc.get_rates()
                    ret[logger][name][status] = cur_vals
                    _update_add(cur_name_vals, cur_vals)
                    _update_add(cur_logger_vals, cur_vals)
                    _update_add(all_loggers_vals, cur_vals)
        return ret

    def __repr__(self):
        cn = self.__class__.__name__
        total_values = self.get_values()['__all__']
        return '<%s total_values=%r>' % (cn,
                                         total_values)


class SensibleSink(object):
    def __init__(self, formatter=None, emitter=None, filters=None, on=None):
        events = on
        if events is None:
            events = ['complete']
        elif isinstance(events, basestring):
            events = [events]
        self.events = [e.lower() for e in events]
        self.filters = list(filters or [])
        self.formatter = formatter
        self.emitter = emitter

        if 'complete' in self.events:
            self.on_complete = self._on_complete
        if 'begin' in self.events:
            self.on_begin = self._on_begin
        # TODO warn and exc

    def _on_complete(self, record):
        if self.filters and not all([f(record) for f in self.filters]):
            return
        entry = self.formatter(record)
        return self.emitter(entry)

    def _on_begin(self, record):
        if self.filters and not all([f(record) for f in self.filters]):
            return
        entry = self.formatter(record)
        return self.emitter(entry)

    def __repr__(self):
        cn = self.__class__.__name__
        return ('<%s filters=%r formatter=%r emitter=%r>'
                % (cn, self.filters, self.formatter, self.emitter))


class QuantileSink(object):
    def __init__(self, use_p2=False):
        """
        There are two approaches for quantile-based stats
        accumulation. A standard, reservoir/replacement strategy
        (QuantileAccumulator) and the P2 approach
        (P2QuantileAccumulator).

        P2 is slower to update, but faster to read, so consider
        setting use_p2 to True if your use case entails more frequent
        stats reading.

        Depending on application/sink usage, a MultiQuantileSink may
        be appropriate to avoid collisions among statistics with the
        same record names. (only if you use the same sink with
        multiple loggers, just look at on_complete and it'll be
        clear.)
        """
        self._qa_type = QuantileAccumulator
        if use_p2:
            self._qa_type = P2QuantileAccumulator
        self.qas = {}

    def on_complete(self, record):
        try:
            acc = self.qas[record.name]
        except KeyError:
            acc = self.qas[record.name] = self._qa_type()
        acc.add(record.duration)

    def __repr__(self):
        cn = self.__class__.__name__
        acc_dict_repr = dict([(rec_name, (acc.count, round(acc.median, 4)))
                              for rec_name, acc in self.qas.items()])
        ret = '<%s %r>' % (cn, acc_dict_repr)
        return ret

    def to_dict(self):
        ret = {}
        for r_name, acc in self.qas.iteritems():
            ret[r_name] = {'count': acc.count,
                           'trimean': acc.trimean,
                           'quantiles': dict(acc.get_quantiles())}
        return ret


class MultiQuantileSink(QuantileSink):
    def on_complete(self, record):
        try:
            logger_accs = self.qas[record.logger.name]
        except KeyError:
            logger_accs = self.qas[record.logger.name] = {}
        try:
            acc = logger_accs[record.name]
        except KeyError:
            acc = logger_accs[record.name] = self._qa_type()

        acc.add(record.duration)

    def __repr__(self):
        cn = self.__class__.__name__
        acc_dict_repr = dict([(lname,
                               dict([(k, (a.count, round(a.median, 4)))
                                     for k, a in a_map.items()]))
                              for lname, a_map in self.qas.items()])
        ret = '<%s %r>' % (cn, acc_dict_repr)
        return ret


if __name__ == '__main__':
    fmtr = Formatter('{begin_timestamp} - {record_status}')
    emtr = StreamEmitter('stderr')
    ss = SensibleSink(formatter=fmtr, emitter=emtr)
    from logger import Logger
    log = Logger('test_ss', [ss])
    with log.debug('hi_task') as t:
        t.warn('everything ok?')
        t.success('doin great')
