import time

from pytest import approx

from lithoxyl import accumulators
from lithoxyl.logger import Logger
from lithoxyl.sinks import RateSink, RateAccumulator


def get_baseline(count):
    start_time = time.time()
    for i in range(count):
        time.sleep(0.02)
    return count / (time.time() - start_time)


def test_rate_sink():
    count = 30
    baseline = get_baseline(count)

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

    # Verify the sink's reported rate tracks the actual measured rate.
    # Using rel=0.15 to allow for timing granularity differences
    # between the sink's internal clock and our external measurement.
    acc = list(sink.acc_map.values())[0]['sleeping']['success']
    acc_rate = acc.get_rate(start_time=sink.creation_time)
    assert acc_rate == approx(total_rate / 2, rel=0.15)

    assert test_rates['__all__'] == approx(total_rate, rel=0.15)
    assert test_rates['exception'] * 2 == approx(total_rate, rel=0.15)

    # Sanity check: instrumented loop should not be catastrophically
    # slower than bare sleep().  The 0.25 factor is deliberately loose
    # to tolerate noisy CI VMs (Mac/Windows GHA runners) while still
    # catching a real performance regression (e.g. accidental O(n^2)).
    assert test_rates['__all__'] >= baseline * 0.25, (
        f'instrumented rate {test_rates["__all__"]:.1f}/s is less than 25%'
        f' of baseline {baseline:.1f}/s -- possible perf regression'
    )

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
