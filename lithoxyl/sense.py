# -*- coding: utf-8 -*-

from logger import BaseLogger
from filters import ThresholdFilter
from emitters import StreamEmitter
from formatters import Formatter
from sinks import SensibleSink, QuantileSink


class SensibleLogger(BaseLogger):
    def __init__(self, name, **kwargs):
        if kwargs:
            raise TypeError('unexpected keyword arguments: %r' % kwargs)
        exc_filter = ThresholdFilter(exception=0)
        exc_formatter = Formatter('!! {exc_type}: {exc_tb_str}')
        exc_emitter = StreamEmitter('stderr')
        exc_log = SensibleSink([exc_filter], exc_formatter, exc_emitter)

        #out_filter = ThresholdFilter()
        # TODO: warn_char (requires len on FormatField)
        out_formatter = Formatter('{status_char} {logger_name}'
                                  ' {record_name} {duration_msecs}')
        out_emitter = StreamEmitter('stderr')
        out_log = SensibleSink([], out_formatter, out_emitter)

        sinks = [QuantileSink(), exc_log, out_log]
        super(SensibleLogger, self).__init__(name, sinks)


if __name__ == '__main__':
    sl = SensibleLogger('test_logger')

    for i in range(3):
        with sl.debug('test_record') as t:
            print 'workin it', i

    with sl.info('test_exception', reraise=False) as te:
        raise ValueError('hm')
