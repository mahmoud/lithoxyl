import math
import pytest
from lithoxyl.accumulators import MaxAccumulator, MinAccumulator, HistogramCounter


# --- MaxAccumulator ---
# Guard: val <= max_list[0] => return (even if not full)
# So values must be added in ascending order to fill, or larger-than-min values.

class TestMaxAccumulator:
    def test_max_default_empty(self):
        ma = MaxAccumulator()
        assert ma.max_list == []
        assert ma.max_len == 10

    def test_max_custom_count(self):
        ma = MaxAccumulator(count=3)
        assert ma.max_len == 3

    def test_max_add_below_capacity(self):
        """Insort path when len < max_len and val > min."""
        ma = MaxAccumulator(count=5)
        ma.add(1)
        ma.add(3)
        ma.add(5)
        assert ma.max_list == [1, 3, 5]

    def test_max_add_below_capacity_rejects_lte_min(self):
        """Guard fires even when not full: val <= max_list[0] => no-op."""
        ma = MaxAccumulator(count=5)
        ma.add(10)
        ma.add(5)  # 5 <= 10, rejected
        assert ma.max_list == [10]

    def test_max_add_fills_capacity(self):
        ma = MaxAccumulator(count=3)
        ma.add(5)
        ma.add(7)
        ma.add(10)
        assert ma.max_list == [5, 7, 10]

    def test_max_add_val_below_min_when_full(self):
        """Line 15-16: val <= max_list[0] when list is full => no-op."""
        ma = MaxAccumulator(count=3)
        for v in [10, 20, 30]:
            ma.add(v)
        assert ma.max_list == [10, 20, 30]
        ma.add(10)  # equal to min
        assert ma.max_list == [10, 20, 30]
        ma.add(5)   # below min
        assert ma.max_list == [10, 20, 30]

    def test_max_add_val_at_end_when_full(self):
        """Lines 22-24: idx == max_len => append + pop(0)."""
        ma = MaxAccumulator(count=3)
        for v in [10, 20, 30]:
            ma.add(v)
        # 40 > 30, bisect_right([10,20,30], 40) = 3 == max_len => append+pop
        ma.add(40)
        assert ma.max_list == [20, 30, 40]

    def test_max_add_val_in_middle_when_full(self):
        """Lines 25-26: idx < max_len => overwrite max_list[idx]."""
        ma = MaxAccumulator(count=3)
        for v in [10, 20, 30]:
            ma.add(v)
        # 25 > 10, bisect_right([10,20,30], 25) = 2, != 3 => max_list[2] = 25
        ma.add(25)
        assert ma.max_list == [10, 20, 25]

    def test_max_add_first_element(self):
        """Empty list: guard 'if max_list' is False, falls through to insort."""
        ma = MaxAccumulator(count=3)
        ma.add(42)
        assert ma.max_list == [42]

    def test_max_add_duplicate_at_min(self):
        """Duplicate equal to min is rejected by guard."""
        ma = MaxAccumulator(count=3)
        ma.add(5)
        ma.add(5)  # 5 <= 5, rejected
        assert ma.max_list == [5]

    def test_max_sequential_ascending(self):
        """Stress the append+pop path repeatedly."""
        ma = MaxAccumulator(count=3)
        for v in range(10):
            ma.add(v)
        assert ma.max_list == [7, 8, 9]

    def test_max_overwrite_path_multiple(self):
        """Exercise overwrite path (idx < max_len) multiple times."""
        ma = MaxAccumulator(count=3)
        ma.add(1)
        ma.add(5)
        ma.add(10)
        assert ma.max_list == [1, 5, 10]
        # 3 > 1, bisect_right([1,5,10], 3) = 1, != 3 => overwrite [1] = 3
        ma.add(3)
        assert ma.max_list == [1, 3, 10]


# --- MinAccumulator ---
# Guard: val >= min_list[-1] => return (even if not full)
# Values must be added in descending order to fill, or smaller-than-max values.

class TestMinAccumulator:
    def test_min_default_empty(self):
        mi = MinAccumulator()
        assert mi.min_list == []
        assert mi.max_len == 10

    def test_min_custom_count(self):
        mi = MinAccumulator(count=4)
        assert mi.max_len == 4

    def test_min_add_below_capacity(self):
        """Insort path when len < max_len and val < max."""
        mi = MinAccumulator(count=5)
        mi.add(5)
        mi.add(3)
        mi.add(1)
        assert mi.min_list == [1, 3, 5]

    def test_min_add_below_capacity_rejects_gte_max(self):
        """Guard fires even when not full: val >= min_list[-1] => no-op."""
        mi = MinAccumulator(count=5)
        mi.add(1)
        mi.add(5)  # 5 >= 1, rejected
        assert mi.min_list == [1]

    def test_min_add_fills_capacity(self):
        mi = MinAccumulator(count=3)
        mi.add(10)
        mi.add(7)
        mi.add(5)
        assert mi.min_list == [5, 7, 10]

    def test_min_add_val_above_max_when_full(self):
        """Lines 38-39: val >= min_list[-1] when full => no-op."""
        mi = MinAccumulator(count=3)
        for v in [30, 20, 10]:
            mi.add(v)
        assert mi.min_list == [10, 20, 30]
        mi.add(30)   # equal to max
        assert mi.min_list == [10, 20, 30]
        mi.add(100)  # above max
        assert mi.min_list == [10, 20, 30]

    def test_min_add_val_at_start_when_full(self):
        """Lines 45-47: idx == 0 => insert(0, val) + pop() path."""
        mi = MinAccumulator(count=3)
        for v in [30, 20, 10]:
            mi.add(v)
        # 5 < 10, bisect_right([10,20,30], 5) = 0 => insert+pop
        mi.add(5)
        assert mi.min_list == [5, 10, 20]

    def test_min_add_val_in_middle_when_full(self):
        """Lines 48-49: idx != 0 => overwrite min_list[idx]."""
        mi = MinAccumulator(count=3)
        for v in [30, 20, 10]:
            mi.add(v)
        # 15 < 30, bisect_right([10,20,30], 15) = 1, != 0 => min_list[1] = 15
        mi.add(15)
        assert mi.min_list == [10, 15, 30]

    def test_min_add_first_element(self):
        mi = MinAccumulator(count=3)
        mi.add(42)
        assert mi.min_list == [42]

    def test_min_add_duplicate_at_max(self):
        """Duplicate equal to max is rejected by guard."""
        mi = MinAccumulator(count=3)
        mi.add(5)
        mi.add(5)  # 5 >= 5, rejected
        assert mi.min_list == [5]

    def test_min_sequential_descending(self):
        """Stress the insert+pop path repeatedly."""
        mi = MinAccumulator(count=3)
        for v in range(9, -1, -1):
            mi.add(v)
        assert mi.min_list == [0, 1, 2]

    def test_min_overwrite_path_multiple(self):
        """Exercise overwrite path (idx != 0) multiple times."""
        mi = MinAccumulator(count=3)
        mi.add(10)
        mi.add(5)
        mi.add(1)
        assert mi.min_list == [1, 5, 10]
        # 8 < 10, bisect_right([1,5,10], 8) = 2, != 0 => overwrite [2] = 8
        mi.add(8)
        assert mi.min_list == [1, 5, 8]


# --- HistogramCounter ---

class TestHistogramCounter:
    def test_histogram_basic(self):
        hc = HistogramCounter([0, 10, 20])
        hc.add(-5)   # bucket (-inf, 0)
        hc.add(5)    # bucket (0, 10)
        hc.add(15)   # bucket (10, 20)
        hc.add(25)   # bucket (20, inf)
        results = hc.get_results()
        ranges = [r for r, _ in results]
        counts = [c for _, c in results]
        assert ranges == [
            (float('-inf'), 0),
            (0, 10),
            (10, 20),
            (20, float('inf')),
        ]
        assert counts == [1, 1, 1, 1]

    def test_histogram_type_error(self):
        with pytest.raises(TypeError, match='expected iterable of numeric ranges'):
            HistogramCounter(['a', 'b', 'c'])

    def test_histogram_nan_error(self):
        with pytest.raises(ValueError, match='expected non-NaN floats'):
            HistogramCounter([0, float('nan'), 10])

    def test_histogram_edge_values(self):
        """Values at exact boundaries go to the bucket to the right."""
        hc = HistogramCounter([0, 10, 20])
        hc.add(0)
        hc.add(10)
        hc.add(20)
        results = hc.get_results()
        counts = [c for _, c in results]
        # (-inf,0)=0, (0,10)=1, (10,20)=1, (20,inf)=1
        assert counts == [0, 1, 1, 1]

    def test_histogram_multiple_adds_same_bucket(self):
        hc = HistogramCounter([0, 10])
        for _ in range(5):
            hc.add(5)
        results = hc.get_results()
        counts = [c for _, c in results]
        assert counts == [0, 5, 0]

    def test_histogram_single_bound(self):
        hc = HistogramCounter([0])
        hc.add(-1)
        hc.add(1)
        results = hc.get_results()
        counts = [c for _, c in results]
        assert counts == [1, 1]

    def test_histogram_duplicate_bounds(self):
        hc = HistogramCounter([0, 0, 10, 10])
        assert len(hc.ranges) == 3

    def test_histogram_get_results_empty(self):
        hc = HistogramCounter([0, 10])
        results = hc.get_results()
        counts = [c for _, c in results]
        assert all(c == 0 for c in counts)
