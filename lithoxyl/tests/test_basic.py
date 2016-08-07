# -*- coding: utf-8 -*-

import sys
import time
import json

from lithoxyl.sinks import AggregateSink
from lithoxyl.logger import Logger


def _get_logger():
    acc = AggregateSink()
    return Logger('test_logger', [acc])


def do_debug_trans(logger):
    with logger.debug('hi') as t:
        time.sleep(0.01)
        t.success('yay')
    return t


def test_logger_success(trans_count=2):
    logger = _get_logger()
    for i in range(trans_count):
        do_debug_trans(logger)
    assert len(logger.sinks[0].end_events) == trans_count
    agg_sink_repr = repr(logger.sinks[0])
    assert 'begins=' in agg_sink_repr
    assert 'begins=0' not in agg_sink_repr

    assert '<Logger' in repr(logger)


def test_callpoint_info():
    log = Logger('test_logger', [])
    t = do_debug_trans(log)
    assert t.callpoint.module_name == __name__
    assert t.callpoint.module_path.endswith(__file__)
    assert t.callpoint.func_name == 'do_debug_trans'
    assert t.callpoint.lineno > 0
    assert t.callpoint.lasti > 0
    assert repr(t)


def test_reraise_false():
    logger = _get_logger()
    with logger.debug('hi', reraise=False) as t:
        x
    assert logger.sinks[0].end_events[0].status == 'exception'


def test_reraise_true():
    logger = _get_logger()
    try:
        with logger.debug('hi', reraise=True) as t:
            y
    except NameError:
        assert True
    else:
        assert False, 'should have reraised NameError'


_MSG_ATTRS = ('name', 'level_name', 'status', 'message',
              'begin_time', 'end_time', 'duration')


class SimpleStructuredFileSink(object):
    def __init__(self, fileobj=None):
        self.fileobj = fileobj or sys.stdout

    def on_end(self, event):
        msg_data = dict(event.data_map)
        for attr in _MSG_ATTRS:
            msg_data[attr] = getattr(event, attr, None)
        json_str = json.dumps(msg_data, sort_keys=True)
        self.fileobj.write(json_str)
        self.fileobj.write('\n')


def test_structured(trans_count=5):
    acc = SimpleStructuredFileSink()
    log = Logger('test_logger', [acc])
    for i in range(trans_count):
        do_debug_trans(log)


def test_dup_sink():
    log = Logger('test_exc_logger')
    agg_sink = AggregateSink()

    log.add_sink(agg_sink)
    log.add_sink(agg_sink)

    assert len(log.sinks) == 1


def test_exception():
    log = Logger('test_exc_logger')

    exc_list = []

    class ExcSink(object):
        def on_exception(self, event, etype, eobj, etb):
            exc_list.append(event)

    exc_sink = ExcSink()
    log.add_sink(exc_sink)

    try:
        with log.critical('raise_act'):
            raise RuntimeError('whooops')
    except RuntimeError:
        pass

    assert len(exc_list) == 1
    assert exc_list[0].exc_info.exc_type == 'RuntimeError'


def test_comment():
    log = Logger('test_comment')

    events = []

    class ComSink(object):
        def on_comment(self, event):
            events.append(event)

    log.add_sink(ComSink())

    log.comment('the first')
    log.comment('the second')

    assert len(events) == 2
