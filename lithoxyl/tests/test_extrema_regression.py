import itertools

import pytest

from lithoxyl.accumulators import MaxAccumulator, MinAccumulator


@pytest.mark.parametrize('capacity', [1, 2, 3, 5])
@pytest.mark.parametrize('values', [
    [10, 5, 1], [1, 5, 10], [5, 5, 5, 5],
    [10, 20, 30, 25], [30, 20, 10, 15], [1, 5, 10, 3],
])
def test_extrema_match_sorted_observations(capacity, values):
    maximum = MaxAccumulator(capacity)
    minimum = MinAccumulator(capacity)
    seen = []
    for value in values:
        seen.append(value)
        maximum.add(value)
        minimum.add(value)
        assert maximum.max_list == sorted(seen)[-capacity:]
        assert minimum.min_list == sorted(seen)[:capacity]


def test_extrema_are_independent_of_insertion_order():
    for values in itertools.permutations([1, 2, 3, 4]):
        maximum = MaxAccumulator(3)
        minimum = MinAccumulator(3)
        for value in values:
            maximum.add(value)
            minimum.add(value)
        assert maximum.max_list == [2, 3, 4]
        assert minimum.min_list == [1, 2, 3]
