# -*- coding: utf-8 -*-

import time

from sinks import AggSink, StructuredFileSink
from logger import BaseLogger


def do_debug_trans(logger):
    with logger.debug('hi') as t:
        time.sleep(0.01)
        t.success('yay')
    return t


def test_logger_success(trans_count=2):
    acc = AggSink()
    log = BaseLogger('test_logger', [acc])
    for i in range(trans_count):
        do_debug_trans(log)
    assert len(acc.messages) == trans_count


def test_structured(trans_count=5):
    acc = StructuredFileSink()
    log = BaseLogger('test_logger', [acc])
    for i in range(trans_count):
        do_debug_trans(log)


def test_callpoint_info():
    log = BaseLogger('test_logger', [])
    t = do_debug_trans(log)
    assert t.callpoint.module_name == __name__
    assert t.callpoint.module_path.endswith(__file__)
    assert t.callpoint.func_name == 'do_debug_trans'
    assert t.callpoint.lineno > 0
    assert t.callpoint.lasti > 0
    assert repr(t)
