"""\

An implementation of P-Squared (Piecewise Parabolic) Quantile
Estimation, which provides efficient online estimation for
quantile-related statistics (e.g., median, quartiles).

For description of the algorithm defined in
http://www.cs.wustl.edu/~jain/papers/ftp/psqr.pdf

Implemented by Kurt Rose and Mahmoud Hashemi (mostly Kurt Rose).

Copyright 2013, 3-clause BSD License
"""

from math import copysign, floor, ceil
from collections import namedtuple

HistogramCell = namedtuple('HistogramCell',
                           'q_range val_range count ratio')


DEFAULT_PERCENTILES = (0.1, 1, 2, 5, 10, 25, 50,
                       75, 80, 85, 90, 95, 98,
                       99, 99.5, 99.8, 99.9, 99.99)


class QuantileAccumulator(object):
    def __init__(self, q_points=DEFAULT_PERCENTILES):
        try:
            qps = sorted([float(x) for x in set(q_points or [])])
            if not qps or not all([0 <= x <= 100 for x in qps]):
                raise ValueError()
        except:
            raise ValueError('invalid quantile point(s): %r' % (q_points,))
        else:
            self._q_points = qps

        self._data = []
        self._is_sorted = True
        self._count = 0
        self._min = float('inf')
        self._max = float('-inf')

    def _sort(self):
        if self._is_sorted:
            return
        self._data.sort()
        self._is_sorted = True

    def add(self, val, idx=None):
        if idx is None:
            idx = -1
        self._data.insert(idx, val)
        self._is_sorted = False
        self._count += 1
        if val < self._min:
            self._min = val
        if val > self._max:
            self._max = val

    def get_quantiles(self):
        ret = [(0.0, self.min)]
        ret.extend([(q, self._get_percentile(q)) for q in self._q_points])
        ret.append((100.0, self.max))
        return ret

    def get_histogram(self):
        # namedtuple may be in order here:
        # need list of: start_q, end_q, start_val, end_val, count, rel_count
        ret = []
        quants = self.get_quantiles()
        for sq, eq in zip(quants, quants[1:]):
            pass
        return ret

    @property
    def count(self):
        return self._count

    @property
    def min(self):
        return self._min

    @property
    def max(self):
        return self._max

    @property
    def range(self):
        return self._min, self._max

    @property
    def median(self):
        return self._get_percentile(50)

    @property
    def quartiles(self):
        gp = self._get_percentile
        return gp(25), gp(50), gp(75)

    @property
    def iqr(self):
        gp = self._get_percentile
        return gp(75) - gp(25)

    @property
    def trimean(self):
        qs = self.quartiles
        return (qs[0] + (2 * qs[1]) + qs[2]) / 4.0

    def _get_percentile(self, percentile=50):
        if not (0 < percentile < 100):
            raise ValueError("it's percentile, not something-else-tile")
        self._sort()
        data, n = self._data, len(self._data)
        idx = percentile / 100.0 * (n - 1)
        idx_f, idx_c = int(floor(idx)), int(ceil(idx))
        if idx_f == idx_c:
            return data[idx_f]
        return (data[idx_f] * (idx - idx_f)) + (data[idx_c] * (idx_c - idx))


class P2Accumulator(object):
    """
    TODO
    ----

    * API
    * fix case where min is requested but _start hasn't been called
    * duplicitous self refs
    * Off-by-two error? 99.9 and 99.99 aren't being returned
    """
    def __init__(self, percentiles=DEFAULT_PERCENTILES):
        self.first_n = []
        self.count = 0
        self.percentiles = percentiles

    def _start(self):
        first_n = sorted(self.first_n)
        self.min = first_n[0]
        self.max = first_n[-1]
        vals = [[i + 1, first_n[i]] for i in range(1, len(first_n) - 1)]
        self.points = zip(self.percentiles, vals)

    def add_val(self, val):
        self.count += 1

        if len(self.first_n) < len(self.percentiles) + 2:
            self.first_n.append(val)
            if len(self.first_n) == len(self.percentiles):
                self._start()
            return

        if val < self.min:
            self.min = val
        if val > self.max:
            self.max = val
        scale = self.count - 1
        # right-most point is stopping case; handle first
        right = self.points[-1][1]
        if val <= right[1]:
            right[0] += 1
            if right[0] == self.count:
                right[0] -= 1
        # handle the rest of the points
        for i in range(len(self.points) - 2, -1, -1):
            point = self.points[i][1]
            if val <= point[1]:
                point[0] += 1
                if point[0] == self.points[i + 1][1][0]:
                    point[0] -= 1
        # left-most point is a special case
        left = self.points[0][1]
        left[1], left[0] = _nxt(1, self.min, left[0], left[1],
                                self.points[1][1][0], self.points[1][1][1],
                                self.points[0][0] / 100.0, scale)
        # update estimated locations of percentiles
        for i in range(1, len(self.points) - 1):
            prev = self.points[i - 1][1]
            point = self.points[i][1]
            nxt = self.points[i + 1][1]
            point[1], point[0] = _nxt(prev[0], prev[1], point[0],
                                      point[1], nxt[0], nxt[1],
                                      self.points[i][0] / 100.0, scale)
        # right-most point is a special case
        right[1], right[0] = _nxt(self.points[-2][1][0], self.points[-2][1][1],
                                  right[0], right[1], self.count, self.max,
                                  self.points[-1][0] / 100.0, scale)

    def get_quantiles(self):
        data = dict([(e[0], e[1][1]) for e in self.points])
        return data

    def __repr__(self):
        return "Measure(%r)" % (self.get_quantiles(),)


def _nxt(left_n, left_q, cur_n, cur_q, right_n, right_q, quantile, scale):
    # calculate desired position
    d = int(scale * quantile + 1 - cur_n)
    if d:
        d = copysign(1, d)  # clamp d at +/- 1
        if left_n < cur_n + d < right_n:  # try parabolic eqn
            nxt_q = cur_q + (d / (right_n - left_n)) * (
                (cur_n - left_n + d) * (right_q - cur_q) / (right_n - cur_n) +
                (right_n - cur_n - d) * (cur_q - left_q) / (cur_n - left_n))
            if not (left_q < nxt_q < right_q):  # fall back on linear eqn
                if d == 1:
                    nxt_q = cur_q + (right_q - cur_q) / (right_n - cur_n)
                elif d == -1:
                    nxt_q = cur_q - (left_q - cur_q) / (left_n - cur_n)
            return nxt_q, cur_n + d
    return cur_q, cur_n


def test_random():
    # test random.random() values; uniformly distributed between 0 and 1,
    # so 50th percentils ie 0.5, etc
    import random
    import time
    nsamples = 10000
    vals = [random.random() for i in range(nsamples)]
    m = P2Accumulator()
    try:
        start = time.time()
        for e in vals:
            m.add_val(e)
        duration = time.time() - start
        tmpl = "processed %d measurements in %f seconds (%f ms each)"
        print tmpl % (nsamples, duration, 1000 * duration / nsamples)
    except:
        import traceback
        import pdb
        traceback.print_exc()
        pdb.post_mortem()
    p = m.get_quantiles()
    for k, v in p.items():
        if 0.9 > (k / 100.0) / v > 1.1:
            print "problem: %s is %s, should be %s" % (k, v, k / 100.0)
    return m


if __name__ == "__main__":
    m1 = test_random()
    import pprint
    pprint.pprint(m1.get_quantiles())
