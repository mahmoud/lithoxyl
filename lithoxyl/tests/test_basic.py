# -*- coding: utf-8 -*-

import time

from lithoxyl.sinks import AggSink, StructuredFileSink
from lithoxyl.logger import Logger


def _get_logger():
    acc = AggSink()
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
    assert len(logger.sinks[0].records) == trans_count


def test_structured(trans_count=5):
    acc = StructuredFileSink()
    log = Logger('test_logger', [acc])
    for i in range(trans_count):
        do_debug_trans(log)


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
    assert logger.sinks[0].records[0].status == 'exception'


def test_reraise_true():
    logger = _get_logger()
    try:
        with logger.debug('hi', reraise=True) as t:
            y
    except NameError:
        assert True
    else:
        assert False, 'should have reraised NameError'
