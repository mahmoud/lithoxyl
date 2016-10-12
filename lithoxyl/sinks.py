# -*- coding: utf-8 -*-

import pdb
import time
import bisect
from collections import deque

from boltons.cacheutils import ThresholdCounter as TCounter

from lithoxyl.emitters import StreamEmitter
from lithoxyl.quantile import ReservoirAccumulator, P2Accumulator, QP_PRAG
from lithoxyl.ewma import EWMAAccumulator, DEFAULT_PERIODS, DEFAULT_INTERVAL


class AggregateSink(object):
    "A simple sink that just aggregates the messages."
    def __init__(self, limit=None):
        self._limit = limit
        self.begin_events = deque(maxlen=limit)
        self.warn_events = deque(maxlen=limit)
        self.end_events = deque(maxlen=limit)
        self.comment_events = deque(maxlen=limit)

    def on_begin(self, begin_event):
        self.begin_events.append(begin_event)

    def on_warn(self, warn_event):
        self.warn_events.append(warn_event)

    def on_end(self, end_event):
        self.end_events.append(end_event)

    def on_comment(self, comment_event):
        self.comment_events.append(comment_event)

    def __repr__(self):
        cn = self.__class__.__name__
        lens = (self._limit, len(self.begin_events), len(self.end_events),
                len(self.warn_events), len(self.comment_events))
        args = (cn,) + lens
        msg = '<%s limit=%r begins=%r ends=%r warns=%r comments=%r>' % args
        return msg


class DevDebugSink(object):
    """Use this to insert debug prompts where exceptions are raised. Pass
    the exception type or iterable of exception types to selectively
    match. Alternatively, pass True for all Exception subtypes.

    """
    def __init__(self, reraise=False, post_mortem=False):
        if reraise is True:
            reraise = Exception
        self.reraise = reraise
        if post_mortem:
            post_mortem = Exception
        self.post_mortem = post_mortem

    def on_exception(self, event, exc_type, exc_obj, exc_tb):
        if self.post_mortem and isinstance(exc_obj, self.post_mortem):
            pdb.post_mortem()
        if self.reraise and isinstance(exc_obj, self.reraise):
            raise exc_type, exc_obj, exc_tb
        return


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
    facilities for actions as they pass through the system.

    It uses a reservoir system for predictable and stable memory
    use. See RateAccumulator for more information.

    A RateSink can be shared across multiple loggers.
    """
    def __init__(self, getter=None, sample_size=128):
        if getter is None:
            def end_time_getter(end_event):
                return end_event.etime
            getter = end_time_getter
        if not callable(getter):
            raise TypeError('expected callable getter, not %r' % getter)
        self.getter = getter
        self.acc_map = {}
        self.sample_size = sample_size
        self.creation_time = time.time()

    def on_end(self, end_event):
        ev = end_event
        name_time_map = self.acc_map.setdefault(ev.logger, {})
        status_time_map = name_time_map.setdefault(ev.name, {})
        try:
            acc = status_time_map[ev.status]
        except Exception:
            acc = RateAccumulator(sample_size=self.sample_size)
            status_time_map[ev.status] = acc
        acc.add(self.getter(ev))

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
        args = (cn, total_rate_all, total_count_all)
        return '<%s total_rate=%.4f total_count=%r>' % args


class EWMASink(object):
    accumulator_type = EWMAAccumulator

    def __init__(self,
                 getter=None,
                 periods=DEFAULT_PERIODS,
                 interval=DEFAULT_INTERVAL):
        if getter is None:
            getter = lambda action: action.duration
        if not callable(getter):
            raise TypeError('expected callable getter, not %r' % getter)
        self.getter = getter
        self.periods = periods
        self.interval = interval
        self.acc_map = {}

    def on_end(self, action):
        name_time_map = self.acc_map.setdefault(action.logger.name, {})
        status_time_map = name_time_map.setdefault(action.name, {})
        try:
            acc = status_time_map[action.status]
        except Exception:
            acc = self.accumulator_type(periods=self.periods,
                                        interval=self.interval)
            status_time_map[action.status] = acc
        value = self.getter(action)
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
        return '<%s total_values=%r>' % (cn, total_values)


class QuantileSink(object):
    def __init__(self, getter=None, **kwargs):
        """There are two approaches for quantile-based stats
        accumulation. A standard, reservoir/replacement strategy
        (QuantileAccumulator) and the P2 approach
        (P2QuantileAccumulator).

        P2 is slower to update, but faster to read. so consider
        setting use_p2 to True if your use case entails more frequent
        stats reading. P2 is also more space-efficient and tends to be
        more accurate for common performance curves.
        """
        if getter is None:
            getter = lambda event: event.duration
        if not callable(getter):
            raise TypeError('expected callable getter, not %r' % getter)
        self.getter = getter

        default_acc = ReservoirAccumulator
        use_p2 = kwargs.pop('use_p2', False)
        if use_p2:
            default_acc = P2Accumulator

        self._acc_type = kwargs.pop('acc_type', default_acc)
        self.q_points = kwargs.pop('q_points', QP_PRAG)

        self.qas = {}

        if kwargs:
            raise TypeError('unexpected keyword arguments: %r' % kwargs.keys())

    def to_dict(self):
        ret = {}
        for log_name, rec_map in self.qas.items():
            ret[log_name] = cur_map = {}
            for rec_name, acc in rec_map.items():
                cur_map[rec_name] = {'count': acc.count,
                                     'trimean': acc.trimean,
                                     'quantiles': dict(acc.get_quantiles())}
        return ret

    def on_end(self, event):
        try:
            logger_accs = self.qas[event.logger.name]
        except KeyError:
            logger_accs = self.qas[event.logger.name] = {}
        try:
            acc = logger_accs[event.name]
        except KeyError:
            acc = self._acc_type(q_points=self.q_points)
            logger_accs[event.name] = acc

        acc.add(self.getter(event))

    def __repr__(self):
        cn = self.__class__.__name__
        acc_dict_repr = dict([(lname,
                               dict([(k, (a.count, round(a.median, 4)))
                                     for k, a in a_map.items()]))
                              for lname, a_map in self.qas.items()])
        ret = '<%s %r>' % (cn, acc_dict_repr)
        return ret


class CounterSink(object):
    def __init__(self, getter=None, threshold=0.001):
        if getter is None:
            getter = lambda end_event: end_event.action.name
        if not callable(getter):
            raise TypeError('expected callable getter, not %r' % (getter,))

        self.getter = getter
        self.threshold = threshold
        self.counter_map = {}

    def on_end(self, end_event):
        ev, ctr_map = end_event, self.counter_map
        try:
            counter = ctr_map[ev.action.logger]
        except KeyError:
            counter = ctr_map[ev.action.logger] = TCounter(self.threshold)

        key = self.getter(end_event)
        counter.add(key)
        return

    def to_dict(self):
        ret = {}
        for logger, counter in self.counter_map.items():
            ret[logger.name] = cur = dict(counter)
            uncommon_count = counter.get_uncommon_count()
            if uncommon_count:
                ret[logger.name]['__missing__'] = uncommon_count
            cur['__all__'] = sum(cur.values())
        return ret
