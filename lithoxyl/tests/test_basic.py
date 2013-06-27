# -*- coding: utf-8 -*-

import time

from sinks import AggSink, StructuredFileSink
from logger import BaseLogger


def do_debug_trans(logger):
    with logger.debug('hi') as t:
        time.sleep(0.01)
        t.success('yay')


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
