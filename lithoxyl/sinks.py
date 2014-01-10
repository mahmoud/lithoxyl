# -*- coding: utf-8 -*-

import sys
import json

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


class CounterSink(object):
    # TODO: incorporate status
    def __init__(self):
        self.counter_map = {}

    def on_complete(self, record):
        try:
            self.counter_map[record.name] += 1
        except KeyError:
            self.counter_map[record.name] = 1

    def __repr__(self):
        return '<%s %r>' % (self.__class__.__name__, self.counter_map)


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
    from logger import BaseLogger
    log = BaseLogger('test_ss', [ss])
    with log.debug('hi_task') as t:
        t.warn('everything ok?')
        t.success('doin great')
