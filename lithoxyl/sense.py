# -*- coding: utf-8 -*-

from logger import BaseLogger
from filters import ThresholdFilter
from emitters import StreamEmitter
from formatters import Formatter
from sinks import SensibleSink, QuantileSink


class SensibleLogger(BaseLogger):
    def __init__(self, name, **kwargs):
        enable_begin = kwargs.pop('enable_begin', True)
        if kwargs:
            raise TypeError('unexpected keyword arguments: %r' % kwargs)
        exc_filter = ThresholdFilter(exception=0)
        exc_formatter = Formatter('!! {exc_type}: {exc_tb_str}')
        exc_emitter = StreamEmitter('stderr')
        exc_sink = SensibleSink(exc_formatter, exc_emitter, [exc_filter])

        #out_filter = ThresholdFilter()
        # TODO: warn_char (requires len on FormatField)
        out_formatter = Formatter('{status_char} {logger_name}'
                                  ' {message} {duration_msecs}')
        out_emitter = StreamEmitter('stdout')
        out_sink = SensibleSink(out_formatter, out_emitter)
        sinks = [QuantileSink(), exc_sink, out_sink]
        if enable_begin:
            beg_filter = ThresholdFilter(begin=0)
            beg_formatter = Formatter('{status_char} {logger_name} {message}')
            beg_sink = SensibleSink(beg_formatter,
                                    out_emitter,
                                    filters=[beg_filter],
                                    on='begin')
            sinks.append(beg_sink)
        super(SensibleLogger, self).__init__(name, sinks)


if __name__ == '__main__':
    sl = SensibleLogger('test_logger')

    for i in range(5):
        with sl.debug('test_record_%s' % i) as t:
            pass

    with sl.info('test_exception', reraise=False) as te:
        raise ValueError('hm')
