import pytest
from lithoxyl.p_squared import P2Estimator, test_random


class TestProcessQPoints:
    def test_single_float(self):
        result = P2Estimator._process_q_points([0.5])
        assert result == (0.5,)

    def test_strips_0_and_1(self):
        result = P2Estimator._process_q_points([0.0, 0.5, 1.0])
        assert result == (0.5,)

    def test_duplicates_collapsed(self):
        result = P2Estimator._process_q_points([0.5, 0.5, 0.25])
        assert result == (0.25, 0.5)

    def test_empty_raises(self):
        with pytest.raises(ValueError, match='invalid quantile'):
            P2Estimator._process_q_points([])

    def test_none_raises(self):
        with pytest.raises(ValueError, match='invalid quantile'):
            P2Estimator._process_q_points(None)

    def test_out_of_range_raises(self):
        with pytest.raises(ValueError, match='invalid quantile'):
            P2Estimator._process_q_points([1.5])

    def test_negative_raises(self):
        with pytest.raises(ValueError, match='invalid quantile'):
            P2Estimator._process_q_points([-0.1])

    def test_non_numeric_raises(self):
        with pytest.raises(ValueError, match='invalid quantile'):
            P2Estimator._process_q_points(['abc'])

    def test_only_0_and_1_raises(self):
        # After stripping 0.0 and 1.0, nothing left
        with pytest.raises(ValueError, match='invalid quantile'):
            P2Estimator._process_q_points([0.0, 1.0])

    def test_multiple_sorted(self):
        result = P2Estimator._process_q_points([0.75, 0.25, 0.5])
        assert result == (0.25, 0.5, 0.75)


class TestP2EstimatorConstruction:
    def test_basic(self):
        est = P2Estimator(q_points=(0.5,), data=list(range(10)))
        quantiles = est.get_quantiles()
        assert isinstance(quantiles, list)
        assert len(quantiles) > 0
        # Each entry is (q_point, estimated_value)
        for q, val in quantiles:
            assert isinstance(q, float)
            assert isinstance(val, (int, float))

    def test_multiple_quantiles(self):
        est = P2Estimator(q_points=(0.25, 0.5, 0.75), data=list(range(100)))
        quantiles = est.get_quantiles()
        # 3 user q_points + 0.0 + 1.0 = 5 points
        assert len(quantiles) == 5
        # Check ordering: q_points should be sorted
        qs = [q for q, v in quantiles]
        assert qs == sorted(qs)

    def test_insufficient_data_raises(self):
        # q_points=(0.5,) -> internal q_points = (0.0, 0.5, 1.0) -> need >= 3 data points
        with pytest.raises(ValueError, match='expected .* or more initial points'):
            P2Estimator(q_points=(0.5,), data=[1, 2])

    def test_exact_minimum_data(self):
        # Exactly 3 data points for 1 quantile
        est = P2Estimator(q_points=(0.5,), data=[3, 1, 2])
        quantiles = est.get_quantiles()
        assert len(quantiles) == 3

    def test_data_sorted_for_initial(self):
        # Initial data is sorted internally regardless of input order
        est = P2Estimator(q_points=(0.5,), data=[10, 1, 5])
        quantiles = est.get_quantiles()
        # min should be 1, max should be 10
        assert quantiles[0][1] == 1
        assert quantiles[-1][1] == 10


class TestP2EstimatorAdd:
    def test_add_many_values(self):
        """Add enough values to trigger both parabolic and linear interpolation."""
        est = P2Estimator(q_points=(0.5,), data=list(range(20)))
        for i in range(20, 1000):
            est.add(i)
        quantiles = est.get_quantiles()
        # Median of 0..999 should be ~499.5
        median_estimate = est._get_quantile(0.5)
        assert 400 < median_estimate < 600

    def test_add_extremes_below_min(self):
        """Adding a value below current min updates _min_point."""
        est = P2Estimator(q_points=(0.5,), data=[10, 20, 30])
        est.add(-100)
        assert est._min_point[1] == -100

    def test_add_extremes_above_max(self):
        """Adding a value above current max updates _max_point."""
        est = P2Estimator(q_points=(0.5,), data=[10, 20, 30])
        est.add(1000)
        assert est._max_point[1] == 1000

    def test_add_value_equal_to_existing(self):
        """Adding a value equal to an existing point."""
        est = P2Estimator(q_points=(0.5,), data=[1, 2, 3])
        est.add(2)  # equal to middle point
        # Should not raise
        quantiles = est.get_quantiles()
        assert len(quantiles) == 3

    def test_linear_fallback(self):
        """Force the linear fallback path by using data with extreme outliers.

        The parabolic estimate can fall outside [lq, rq] when data is highly
        skewed, causing the algorithm to fall back to linear interpolation.
        """
        # Start with tight cluster, then add extreme outliers
        initial = [1, 2, 3, 4, 5]
        est = P2Estimator(q_points=(0.25, 0.5, 0.75), data=initial)

        # Add extreme values to force parabolic estimate out of bounds
        for _ in range(50):
            est.add(1000000)
        for _ in range(50):
            est.add(-1000000)
        for _ in range(50):
            est.add(0)

        # Should still produce valid quantiles without error
        quantiles = est.get_quantiles()
        assert len(quantiles) == 5

    def test_linear_fallback_d_negative(self):
        """Exercise the d == -1 branch of linear fallback.

        When d < 0 and parabolic fails, uses: nq = cq - (lq - cq) / (ln - cn)
        """
        # Create estimator with ascending data
        initial = list(range(1, 6))
        est = P2Estimator(q_points=(0.25, 0.5, 0.75), data=initial)

        # Push data heavily to the right, then add very small values
        # to create conditions where d becomes negative
        for i in range(100):
            est.add(1000 + i)
        for i in range(200):
            est.add(-1000 - i)

        quantiles = est.get_quantiles()
        assert len(quantiles) == 5

    def test_back_tuples_increment_decrement(self):
        """Exercise the path where point[0] == nxt_point[0] after increment,
        causing decrement (line 68: point[0] -= 1)."""
        # Small dataset where counts can collide
        est = P2Estimator(q_points=(0.5,), data=[1, 2, 3])
        # Add values that are <= existing points to trigger the increment path
        est.add(1)
        est.add(1)
        est.add(2)
        est.add(2)
        quantiles = est.get_quantiles()
        assert len(quantiles) == 3


class TestGetQuantile:
    def test_get_quantile_specific(self):
        est = P2Estimator(q_points=(0.5,), data=list(range(100)))
        result = est._get_quantile(0.5)
        assert isinstance(result, (int, float))
        # Should be close to median of 0..99 = 49.5
        assert 30 < result < 70

    def test_get_quantile_not_tracked(self):
        est = P2Estimator(q_points=(0.5,), data=list(range(10)))
        with pytest.raises(ValueError, match='quantile not tracked'):
            est._get_quantile(0.99)

    def test_get_quantile_boundaries(self):
        """0.0 and 1.0 are always tracked (min and max)."""
        est = P2Estimator(q_points=(0.5,), data=list(range(10)))
        min_val = est._get_quantile(0.0)
        max_val = est._get_quantile(1.0)
        assert min_val == 0
        assert max_val == 9

    def test_get_quantile_string_coerced(self):
        """_get_quantile converts to float, so '0.5' should work."""
        est = P2Estimator(q_points=(0.5,), data=list(range(10)))
        result = est._get_quantile('0.5')
        assert isinstance(result, (int, float))


class TestGetQuantiles:
    def test_format(self):
        est = P2Estimator(q_points=(0.25, 0.5, 0.75), data=list(range(50)))
        quantiles = est.get_quantiles()
        assert isinstance(quantiles, list)
        for item in quantiles:
            assert isinstance(item, tuple)
            assert len(item) == 2

    def test_quantile_ordering(self):
        """Estimated values should be monotonically non-decreasing."""
        est = P2Estimator(q_points=(0.1, 0.25, 0.5, 0.75, 0.9), data=list(range(200)))
        quantiles = est.get_quantiles()
        values = [v for q, v in quantiles]
        for i in range(len(values) - 1):
            assert values[i] <= values[i + 1]


class TestTestRandom:
    def test_runs_without_error(self):
        """test_random should complete without raising. Use small nsamples."""
        # test_random has a pdb.post_mortem() in its except block, so
        # we must ensure it does NOT raise. With valid random data it shouldn't.
        result = test_random(nsamples=1000)
        assert result is None

    def test_with_provided_vals(self):
        """Pass explicit vals to skip internal random generation."""
        vals = list(range(500))
        result = test_random(vals=vals, nsamples=500)
        assert result is None
