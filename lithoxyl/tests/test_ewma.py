from unittest.mock import patch, PropertyMock
import pytest

from lithoxyl.ewma import EWMAAccumulator, DEFAULT_PERIODS, DEFAULT_INTERVAL


class TestConstruction:
    def test_construct_defaults(self):
        with patch('lithoxyl.ewma.time') as mock_time:
            mock_time.time.return_value = 1000.0
            ewma = EWMAAccumulator()
        assert set(ewma._rate_map.keys()) == set(DEFAULT_PERIODS)
        assert len(ewma._rate_map) == 3
        assert ewma._interval == float(DEFAULT_INTERVAL)
        assert ewma._interval == 5.0
        for v in ewma._rate_map.values():
            assert v is None

    def test_construct_custom(self):
        with patch('lithoxyl.ewma.time') as mock_time:
            mock_time.time.return_value = 1000.0
            ewma = EWMAAccumulator(periods=(10, 30), interval=2)
        assert set(ewma._rate_map.keys()) == {10, 30}
        assert ewma._interval == 2.0

    def test_interval_zero_uses_default(self):
        # interval=0 is falsy, so `0 or DEFAULT_INTERVAL` picks the default
        with patch('lithoxyl.ewma.time') as mock_time:
            mock_time.time.return_value = 1000.0
            ewma = EWMAAccumulator(interval=0)
        assert ewma._interval == float(DEFAULT_INTERVAL)

    def test_interval_negative_raises(self):
        with pytest.raises(ValueError, match='interval must be greater than 0'):
            EWMAAccumulator(interval=-1)

    def test_interval_none_uses_default(self):
        with patch('lithoxyl.ewma.time') as mock_time:
            mock_time.time.return_value = 1000.0
            ewma = EWMAAccumulator(interval=None)
        assert ewma._interval == float(DEFAULT_INTERVAL)


class TestAdd:
    def test_add_accumulates(self):
        with patch('lithoxyl.ewma.time') as mock_time:
            mock_time.time.return_value = 1000.0
            ewma = EWMAAccumulator()
        ewma.add(5)
        ewma.add(3)
        assert ewma._uncounted == 8.0

    def test_add_zero(self):
        with patch('lithoxyl.ewma.time') as mock_time:
            mock_time.time.return_value = 1000.0
            ewma = EWMAAccumulator()
        ewma.add(0)
        assert ewma._uncounted == 0.0

    def test_add_negative(self):
        with patch('lithoxyl.ewma.time') as mock_time:
            mock_time.time.return_value = 1000.0
            ewma = EWMAAccumulator()
        ewma.add(-3)
        assert ewma._uncounted == -3.0


class TestGetRates:
    @patch('lithoxyl.ewma.time')
    def test_first_call_forces_update(self, mock_time):
        mock_time.time.return_value = 1000.0
        ewma = EWMAAccumulator(interval=5)
        ewma.add(10)
        # First get_rates should force update due to _force_next_update=True
        mock_time.time.return_value = 1001.0  # only 1s elapsed, < interval
        rates = ewma.get_rates()
        # All periods should have non-None values after forced update
        for period in DEFAULT_PERIODS:
            assert rates[period] is not None
        # _uncounted should be reset after update
        assert ewma._uncounted == 0

    @patch('lithoxyl.ewma.time')
    def test_within_interval_no_update_after_forced(self, mock_time):
        mock_time.time.return_value = 1000.0
        ewma = EWMAAccumulator(interval=5)
        ewma.add(10)
        # Force the first update
        mock_time.time.return_value = 1001.0
        rates1 = ewma.get_rates()
        # Add more but stay within interval
        ewma.add(20)
        mock_time.time.return_value = 1002.0  # 1s since last update, < 5s interval
        rates2 = ewma.get_rates()
        # Rates should not change since we're within interval and force flag is consumed
        assert rates1 == rates2
        # _uncounted should still hold the new value (not reset)
        assert ewma._uncounted == 20

    @patch('lithoxyl.ewma.time')
    def test_after_interval_updates(self, mock_time):
        mock_time.time.return_value = 1000.0
        ewma = EWMAAccumulator(interval=5)
        ewma.add(10)
        # Force first update
        mock_time.time.return_value = 1001.0
        rates1 = ewma.get_rates()
        # Add more and advance past interval
        ewma.add(50)
        mock_time.time.return_value = 1007.0  # 6s since last update > 5s interval
        rates2 = ewma.get_rates()
        # Rates should have changed
        assert rates1 != rates2
        # _uncounted should be reset
        assert ewma._uncounted == 0

    @patch('lithoxyl.ewma.time')
    def test_get_rates_returns_copy(self, mock_time):
        mock_time.time.return_value = 1000.0
        ewma = EWMAAccumulator(interval=5)
        # Advance time so forced update doesn't divide by zero
        mock_time.time.return_value = 1001.0
        rates = ewma.get_rates()
        rates[60] = 'tampered'
        assert ewma._rate_map[60] != 'tampered'


class TestUpdate:
    @patch('lithoxyl.ewma.time')
    def test_update_initializes_none_rates(self, mock_time):
        """When rate_map values are None, _update sets them to new_rate directly."""
        mock_time.time.return_value = 1000.0
        ewma = EWMAAccumulator(periods=(60,), interval=5)
        ewma.add(20)
        # Trigger forced update
        mock_time.time.return_value = 1002.0
        ewma.get_rates()
        # rate = uncounted / interval = 20 / 2 = 10.0
        assert ewma._rate_map[60] == pytest.approx(10.0)

    @patch('lithoxyl.ewma.time')
    def test_update_decays_existing_rates(self, mock_time):
        """When rate_map already has values, _update applies EWMA decay."""
        import math
        mock_time.time.return_value = 1000.0
        ewma = EWMAAccumulator(periods=(60,), interval=5)
        ewma.add(20)
        # First update (forced)
        mock_time.time.return_value = 1002.0
        ewma.get_rates()
        initial_rate = ewma._rate_map[60]
        # Second update with different value
        ewma.add(100)
        mock_time.time.return_value = 1008.0  # 6s past last update
        ewma.get_rates()
        interval = 6.0
        new_rate = 100.0 / interval
        alpha = 1 - math.exp(-interval / 60)
        expected = initial_rate + alpha * (new_rate - initial_rate)
        assert ewma._rate_map[60] == pytest.approx(expected)

    @patch('lithoxyl.ewma.time')
    def test_update_resets_uncounted(self, mock_time):
        mock_time.time.return_value = 1000.0
        ewma = EWMAAccumulator(interval=5)
        ewma.add(42)
        mock_time.time.return_value = 1001.0
        ewma.get_rates()  # triggers forced update
        assert ewma._uncounted == 0

    @patch('lithoxyl.ewma.time')
    def test_update_sets_last_update(self, mock_time):
        mock_time.time.return_value = 1000.0
        ewma = EWMAAccumulator(interval=5)
        mock_time.time.return_value = 1001.0
        ewma.get_rates()  # forced
        assert ewma._last_update == 1001.0


class TestRepr:
    @patch('lithoxyl.ewma.time')
    def test_repr_contains_class_and_rates(self, mock_time):
        mock_time.time.return_value = 1000.0
        ewma = EWMAAccumulator()
        mock_time.time.return_value = 1001.0
        r = repr(ewma)
        assert 'EWMAAccumulator' in r
        assert 'rates=' in r

    @patch('lithoxyl.ewma.time')
    def test_repr_calls_get_rates(self, mock_time):
        mock_time.time.return_value = 1000.0
        ewma = EWMAAccumulator()
        ewma.add(5)
        mock_time.time.return_value = 1001.0
        r = repr(ewma)
        # repr triggers get_rates which triggers forced update
        assert ewma._uncounted == 0


class TestRateConvergence:
    @patch('lithoxyl.ewma.time')
    def test_rate_converges_toward_actual(self, mock_time):
        """Add a steady stream at known rate, verify EWMA converges."""
        mock_time.time.return_value = 1000.0
        ewma = EWMAAccumulator(periods=(10,), interval=1)

        # Simulate adding 1 unit per second for 50 seconds
        for i in range(50):
            t = 1000.0 + (i + 1)
            mock_time.time.return_value = t
            ewma.add(1)
            ewma.get_rates()

        # Don't call get_rates again at same timestamp (would cause div-by-zero)
        # Last rates from the loop are sufficient
        rates = ewma._rate_map.copy()
        # With 1 unit added per 1-second interval, rate should converge to ~1.0
        assert rates[10] == pytest.approx(1.0, abs=0.05)


class TestMain:
    @patch('lithoxyl.ewma.time')
    @patch('builtins.print')
    def test_main_runs(self, mock_print, mock_time):
        # Simulate time advancing so all loops complete quickly.
        # _main has speed_counts = [(0.5, 1), (0.2, 5), (0.5, 10)]
        # Total iterations = 1 + 5 + 10 = 16, each needs dur > speed.
        # Also needs to hit print branch (print_dur > 0.2).
        call_count = [0]

        def advancing_time():
            call_count[0] += 1
            # Each call returns a value 1s later than init time
            return 1000.0 + call_count[0]

        mock_time.time.side_effect = advancing_time
        mock_time.sleep.return_value = None

        from lithoxyl.ewma import _main
        _main(incr=1)

        # _main should have called print at least once
        assert mock_print.called
