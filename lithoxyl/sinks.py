# -*- coding: utf-8 -*-

import sys
import json

from filters import ThresholdFilter
from formatters import Templette


class AggSink(object):
    "A 'dummy' sink that just aggregates the messages."
    def __init__(self):
        self.records = []

    def handle_start(self, record):
        pass

    def handle(self, record):
        self.records.append(record)


_MSG_ATTRS = ('name', 'level', 'status', 'message',
              'start_time', 'end_time', 'duration')


class StructuredFileSink(object):
    def __init__(self, fileobj=None):
        self.fileobj = fileobj or sys.stdout

    def handle(self, record):
        msg_data = dict(record.extras)
        for attr in _MSG_ATTRS:
            msg_data[attr] = getattr(record, attr, None)
        json_str = json.dumps(msg_data, sort_keys=True)
        self.fileobj.write(json_str)
        self.fileobj.write('\n')


def tmp_emitter(entry):
    print entry


class SensibleSink(object):
    def __init__(self, filters=None, formatter=None, emitter=None):
        self.filters = list(filters or [])
        self.formatter = formatter
        self.emitter = emitter

    def handle(self, record):
        if self.filters and not all([f(record) for f in self.filters]):
            return
        entry = self.formatter(record)
        return self.emitter(entry)


if __name__ == '__main__':
    fmtr = Templette('{start_timestamp} - {record_status}')
    ss = SensibleSink(formatter=fmtr, emitter=tmp_emitter)
    from logger import BaseLogger
    log = BaseLogger('test_ss', [ss])
    with log.debug('hi_task') as t:
        t.warn('everything ok?')
        t.success('doin great')


"""
Vocabangst:

* Start: begin, open, init
* Stop: finish, complete, close, (commit?)
"""
