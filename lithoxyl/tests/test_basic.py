# -*- coding: utf-8 -*-

from sinks import AggSink
from logger import BaseLogger


def do_debug_trans(logger):
    with logger.debug('hi') as t:
        t.success('yay')


def test_logger_success(trans_count=2):
    acc = AggSink()
    log = BaseLogger('test_logger', [acc])
    for i in range(trans_count):
        do_debug_trans(log)
    assert len(acc.messages) == trans_count
