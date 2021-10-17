# -*- coding: utf-8 -*-

from __future__ import absolute_import
import sys
import time

from lithoxyl.logger import Logger
from lithoxyl.sinks import RateSink, RateAccumulator

IS_PYPY = '__pypy__' in sys.builtin_module_names

def test_rate_sink():
    sink = RateSink()
    logger = Logger('testlog', sinks=[sink])

    for i in range(10):
        with logger.info('sleeping', reraise=False):
            time.sleep(0.02)
            if i % 2:
                raise ValueError()
    test_rates = sink.get_rates()['testlog']['sleeping']
    # TODO: these are a little flaky, esp when moving between
    # environments, runtimes, and with/without coverage, hence the
    # range
    all_lower_limit = 40 if IS_PYPY else 47
    assert all_lower_limit <= round(test_rates['__all__']) <= 51
    assert 21 <= round(test_rates['exception']) <= 26

    counts = sink.get_total_counts()
    assert counts['__all__'] == 10

    assert repr(sink)


def test_rate_acc():
    acc = RateAccumulator()
    target_rate = 2000
    incr = 1.0 / target_rate
    start_time = cur_time = time.time()

    for i in range(1000):
        acc.add(cur_time)
        cur_time = start_time + (incr * i)

    rate = acc.get_rate(start_time=start_time, end_time=cur_time)
    assert target_rate - 2.5 <= rate <= target_rate + 2.5

    new_rate = acc.get_rate(start_time=start_time + 0.5, end_time=cur_time)
    assert round(new_rate - rate, -2) == 0
    # TODO: check the math on the above. It's the "if not count" block
    # in the RateAccumulator. might have an off-by-one

    assert repr(acc)
