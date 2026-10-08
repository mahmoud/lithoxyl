import pytest

from lithoxyl.ewma import EWMAAccumulator


@pytest.mark.parametrize('first_elapsed', [0, -1])
def test_initial_rate_waits_for_positive_elapsed_time(monkeypatch, first_elapsed):
    clock = [1000.0]
    monkeypatch.setattr('lithoxyl.ewma.time.time', lambda: clock[0])
    accumulator = EWMAAccumulator(periods=(60,), interval=5)
    accumulator.add(10)
    clock[0] += first_elapsed
    assert accumulator.get_rates() == {60: None}
    clock[0] = 1001.0
    assert accumulator.get_rates() == {60: 10.0}


def test_first_interval_update_is_not_repeated(monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr('lithoxyl.ewma.time.time', lambda: clock[0])
    accumulator = EWMAAccumulator(periods=(60,), interval=5)
    accumulator.add(10)
    clock[0] = 1005.0
    assert accumulator.get_rates() == {60: 2.0}
    assert accumulator.get_rates() == {60: 2.0}
    assert 'rates=' in repr(accumulator)
