"""\

An implementation of P-Squared (Piecewise Parabolic) Quantile
Estimation, which provides efficient online estimation for
quantile-related statistics (e.g., median, quartiles).

For description of the algorithm defined in
http://www.cs.wustl.edu/~jain/papers/ftp/psqr.pdf

Implemented by Kurt Rose and Mahmoud Hashemi.

Copyright 2013, 3-clause BSD License
"""

import array
import random

from math import copysign, floor, ceil
from collections import namedtuple

HistogramCell = namedtuple('HistogramCell',
                           'q_range val_range ratio count')


P2_MIN = (25.0, 50.0, 75.0)
P2_PRAG = (1.0, 5.0, 25.0, 50.0, 75.0, 90.0, 95.0, 99.0)
P2_PRO = (0.1, 1, 2, 5, 10, 25, 50,
          75, 80, 85, 90, 95, 98,
          99, 99.5, 99.8, 99.9, 99.99)


class BaseQuantileAccumulator(object):  # TODO: ABC makin a comeback?
    def __init__(self):
        self._count = 0
        self._min = float('inf')
        self._max = float('-inf')

    def add(self, val, idx=None):
        self._count += 1
        if val < self._min:
            self._min = val
        if val > self._max:
            self._max = val

    def get_quantiles(self, q_points=None):
        q_points = q_points or []
        ret = [(0.0, self.min)]
        ret.extend([(q, self._get_quantile(q)) for q in q_points])
        ret.append((100.0, self.max))
        return ret

    def get_histogram(self):
        """\
        This convenience method gives back an estimated histogram, based
        on quantiles from get_quantiles(). It's mostly just a utility
        for rendering graphs; it's no more accurate than
        get_quantiles(), and probably even less so for very small
        dataset-size-to-bucket-count ratios.

        TODO: Because it stores observations, this BasicAccumulator
        could actually give back a real histogram, too.
        """
        ret = []
        qwantz = self.get_quantiles()
        total_count = self.count
        for sq, eq in zip(qwantz, qwantz[1:]):
            q_range = start_q, end_q = sq[0], eq[0]
            val_range = start_val, end_val = sq[1], eq[1]
            ratio = (end_q - start_q) / 100.0
            count = int(ratio * total_count)
            if total_count < len(qwantz):
                if end_val > start_val:
                    count += 1  # not exactly, but sorta.
            else:
                if start_q == 0.0 or end_q == 100.0:
                    count += 1  # make range inclusive
            ret.append(HistogramCell(q_range, val_range, ratio, count))
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
        return self._get_quantile(50)

    @property
    def quartiles(self):
        gq = self._get_quantile
        return gq(25), gq(50), gq(75)

    @property
    def iqr(self):
        gq = self._get_quantile
        return gq(75) - gq(25)

    @property
    def trimean(self):
        qs = self.quartiles
        return (qs[0] + (2 * qs[1]) + qs[2]) / 4.0


class QuantileAccumulator(BaseQuantileAccumulator):
    def __init__(self, data=None, cap=None):
        super(QuantileAccumulator, self).__init__()
        self._typecode = 'f'  # TODO
        self._data = array.array(self._typecode)
        self._is_sorted = True
        if cap is None:
            self._cap = float('inf')
        elif cap is True:
            self._cap = 2 ** 14
        else:
            self._cap = int(cap)
        data = data or []
        for v in data:
            self.add(v)

    def _sort(self):
        if self._is_sorted:
            return
        if callable(getattr(self._data, 'sort', None)):
            self._data.sort()
        else:
            self._data = array.array(self._typecode, sorted(self._data))
        self._is_sorted = True

    def add(self, val):
        if self._count < self._cap:
            self._data.append(val)
            self._is_sorted = False
            super(QuantileAccumulator, self).add(val)
        else:
            idx = random.randint(0, self._count)
            if idx < self._cap:
                self._data[idx] = val
                self._is_sorted = False
                super(QuantileAccumulator, self).add(val)

    def _get_quantile(self, q=50):
        if not (0 < q < 100):
            raise ValueError('expected a value in range 0-100 (non-inclusive)')
        self._sort()
        data, n = self._data, len(self._data)
        idx = q / 100.0 * (n - 1)
        idx_f, idx_c = int(floor(idx)), int(ceil(idx))
        if idx_f == idx_c:
            return data[idx_f]
        return (data[idx_f] * (idx_c - idx)) + (data[idx_c] * (idx - idx_f))


class P2QuantileAccumulator(BaseQuantileAccumulator):
    # TODO: configurable qps
    # TODO: preprocess qps
    # TODO: fix min/max, etc.

    def __init__(self, data=None):
        super(P2QuantileAccumulator, self).__init__()
        data = data or []
        self._q_points = P2_PRO
        self._tmp_acc = QuantileAccumulator(cap=None)
        self._thresh = len(self._q_points) + 2
        self._est = None

        for v in data:
            self.add(v)

    def add(self, val):
        if self._est is None:
            ta = self._tmp_acc
            ta.add(val)
            if ta.count >= self._thresh:
                self._est = P2Estimator(self._q_points, ta._data)
                self._tmp_acc = None
            return
        else:
            self._est.add(val)
        super(P2QuantileAccumulator, self).add(val)

    def get_quantiles(self, q_points=None):
        q_points = q_points or self._q_points  # blargh hack
        return super(P2QuantileAccumulator, self).get_quantiles(q_points)

    def _get_quantile(self, q):
        try:
            return self._est._get_quantile(q)
        except AttributeError:
            return self._tmp_acc._get_quantile(q)


class P2Estimator(object):
    def __init__(self, q_points, data):
        self._q_points = self._process_q_points(q_points)
        self._q_points = (0.0,) + self._q_points + (100.0,)
        len_data, len_qps = len(data), len(self._q_points)
        if len_data < len_qps:
            msg = ('expected %d or more initial points for '
                   '%d quantiles (got %d)' % (len_qps, len_qps - 2, len_data))
            raise ValueError(msg)

        initial = sorted(data[:len_qps])
        vals = [[i + 1, x] for i, x in enumerate(initial)]
        self._points = pts = zip(self._q_points, vals)  # TODO: marks?
        self._min_point, self._max_point = pts[0][1], pts[-1][1]
        self._lookup = dict(pts)
        self._back_tuples = list(reversed(zip(vals[1:], vals[2:])))
        self._quads = zip(self._q_points[1:], vals, vals[1:], vals[2:])

        for i in xrange(len_qps, len_data):
            self.add(data[i])

    @staticmethod
    def _process_q_points(q_points):
        try:
            qps = sorted([float(x) for x in set(q_points or [])])
            if qps[0] == 0.0:
                qps = qps[1:]
            if qps[-1] == 100.0:
                qps = qps[:-1]
            if not qps or not all([0 <= x <= 100 for x in qps]):
                raise ValueError()
        except:
            raise ValueError('invalid quantile point(s): %r' % (q_points,))
        else:
            return tuple(qps)

    def add(self, val):
        prev_count = self._max_point[0]
        self._max_point[0] = prev_count + 1

        cur_min, cur_max = self._min_point[1], self._max_point[1]
        if val < cur_min:
            self._min_point[1] = cur_min = val
        elif val > cur_max:
            self._max_point[1] = cur_max = val

        for point, nxt_point in self._back_tuples:
            if val <= point[1]:
                point[0] += 1
                if point[0] == nxt_point[0]:
                    point[0] -= 1

        # update estimated locations of percentiles
        for qp, left, cur, right in self._quads:
            (ln, lq), (cn, cq), (rn, rq) = left, cur, right
            d = int(prev_count * (qp / 100.0) + 1 - cn)
            if not d:
                continue
            d = 1.0 if d > 0 else -1.0  # clamped at +-1
            if not (ln < cn + d < rn):
                continue
            nq = (cq + (d / (rn - ln)) *  # hooray parabolic
                  ((cn - ln + d) * (rq - cq) / (rn - cn) +
                   (rn - cn - d) * (cq - lq) / (cn - ln)))
            if not (lq < nq < rq):  # fall back on linear eqn
                if d == 1:
                    nq = cq + (rq - cq) / (rn - cn)
                elif d == -1:
                    nq = cq - (lq - cq) / (ln - cn)
            cur[0], cur[1] = cn + d, nq

    def _get_quantile(self, q):
        try:
            return self._lookup[float(q)][1]
        except KeyError:
            raise ValueError('quantile not tracked: %r' % q)


def test_random(vals=None, nsamples=100000):
    import random
    import time
    from pprint import pprint
    if not vals:
        vals = [random.random() for i in range(nsamples)]
    try:
        start = time.time()
        m = P2QuantileAccumulator(vals)
        p = m.get_quantiles()
        duration = time.time() - start
        tmpl = "P2QA processed %d measurements in %f seconds (%f ms each)"
        print tmpl % (nsamples, duration, 1000 * duration / nsamples)
        pprint(p)
    except:
        import traceback
        import pdb
        traceback.print_exc()
        pdb.post_mortem()
        raise
    for k, v in p:
        if not k:
            continue
        if not 0.95 < v / (k / 100.0) < 1.05:
            print "problem: %s is %s, should be ~%s" % (k, v, k / 100.0)

    start = time.time()
    qa = QuantileAccumulator()
    for i, val in enumerate(vals):
        qa.add(val)
        #if i and i % 1000:
        #    qa.get_quantiles()
    pd = qa.get_quantiles(P2_PRO)
    pprint(pd)
    for k, v in pd:
        if not k:
            continue
        if not 0.95 < v / (k / 100.0) < 1.05:
            print "problem: %s is %s, should be ~%s" % (k, v, k / 100.0)
    duration = time.time() - start
    tmpl = "QA processed %d measurements in %f seconds (%f ms each)"
    print tmpl % (nsamples, duration, 1000 * duration / nsamples)

    return m


if __name__ == "__main__":
    import json
    vals = json.load(open('tmp_test.json'))
    m1 = test_random(vals)
