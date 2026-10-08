import math
from bisect import bisect_right, insort

# TODO: trivial to implement reset on these, but recreation might be better practice?


class MaxAccumulator(object):
    # max_list is sorted in ascending order
    def __init__(self, count=10):
        self.max_list = []
        self.max_len = count

    def add(self, val):
        max_list, max_len = self.max_list, self.max_len
        if len(max_list) >= max_len and (not max_list or val <= max_list[0]):
            return
        insort(max_list, val)
        if len(max_list) > max_len:
            max_list.pop(0)
        return


class MinAccumulator(object):
    # min_list is sorted in ascending order
    def __init__(self, count=10):
        self.min_list = []
        self.max_len = count

    def add(self, val):
        min_list, max_len = self.min_list, self.max_len
        if len(min_list) >= max_len and (not min_list or val >= min_list[-1]):
            return
        insort(min_list, val)
        if len(min_list) > max_len:
            min_list.pop()
        return


class HistogramCounter(object):
    def __init__(self, bounds):
        try:
            bounds_float = [float(b) for b in bounds]
        except ValueError:
            raise TypeError('expected iterable of numeric ranges, not %r'
                            % (bounds,))
        if any([math.isnan(b) for b in bounds_float]):
            raise ValueError('expected non-NaN floats, not %r' % (bounds,))
        bounds_set = set(bounds_float)

        bounds_set.add(float('inf'))
        bounds_set.add(float('-inf'))
        bounds_sorted = sorted(bounds_set)
        self.bounds = bounds_sorted
        self.ranges = [(b1, b2) for b1, b2 in
                       zip(bounds_sorted, bounds_sorted[1:])]
        self.buckets = [0] * len(self.ranges)

    def add(self, val):
        bucket_idx = bisect_right(self.bounds, val) - 1
        self.buckets[bucket_idx] += 1
        return

    def get_results(self):
        return list(zip(self.ranges, self.buckets))
