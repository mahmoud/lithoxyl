# -*- coding: utf-8 -*-

from __future__ import absolute_import
import sys
import time

from pytest import approx

from lithoxyl import accumulators
from lithoxyl.logger import Logger
from lithoxyl.sinks import RateSink, RateAccumulator

IS_PYPY = '__pypy__' in sys.builtin_module_names


def get_baseline(count=10):
    start_time = time.time()
    for i in range(count):
        time.sleep(0.02)
    return count / (time.time() - start_time)


def test_rate_sink():
    # some handy timeit for benching the sink:
    #$ python3 -m timeit -s "import time; import lithoxyl; from lithoxyl.sinks import RateSink, RateAccumulator; from lithoxyl.logger import Logger; sink = RateSink(); logger = Logger('testlog', sinks=[sink]);" "with logger.info('sleeping', reraise=False):" "  time.sleep(0.02); 1/0"
    count = 10
    baseline = get_baseline(count)
    upper_limit, lower_limit = baseline, baseline * (0.75 if IS_PYPY else 0.85)
    assert lower_limit > (35 if IS_PYPY else 38), 'unexpectedly low baseline'

    sink = RateSink()
    logger = Logger('testlog', sinks=[sink])

    start_time = time.time()
    for i in range(count):
        with logger.info('sleeping', reraise=False):
            time.sleep(0.02)
            if i % 2:
                raise ValueError()
    total_time = time.time() - start_time
    total_rate = count / total_time
    test_rates = sink.get_rates()['testlog']['sleeping']

    acc = list(sink.acc_map.values())[0]['sleeping']['success']
    acc_rate = acc.get_rate(start_time=sink.creation_time)
    assert acc_rate == approx(total_rate / 2, rel=0.15)

    assert lower_limit <= test_rates['__all__'] <= upper_limit
    assert lower_limit <= test_rates['exception'] * 2 <= upper_limit

    counts = sink.get_total_counts()
    assert counts['__all__'] == count

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
