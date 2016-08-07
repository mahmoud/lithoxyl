# -*- coding: utf-8 -*-

import array
import random
from math import floor, ceil
from collections import namedtuple

from lithoxyl.p_squared import P2Estimator


HistogramCell = namedtuple('HistogramCell',
                           'q_range val_range ratio count')


QP_MIN = (0.25, 0.50, 0.75)
QP_PRAG = (0.01, 0.05, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99)
QP_PRO = (0.001, 0.01, 0.02, 0.05, 0.10,
          0.25, 0.50, 0.75, 0.80, 0.85, 0.90, 0.95,
          0.98, 0.99, 0.995, 0.998, 0.999, 0.9999)


class BaseQuantileAccumulator(object):
    def __init__(self, q_points=None):
        self._count = 0
        self._min = float('inf')
        self._max = float('-inf')
        self._q_points = q_points or QP_PRAG

    def add(self, val, idx=None):
        self._count += 1
        if val < self._min:
            self._min = val
        if val > self._max:
            self._max = val

    def get_quantiles(self, q_points=None):
        q_points = q_points or self._q_points
        ret = [(0.0, self.min)]
        ret.extend([(q, self._get_quantile(q)) for q in q_points])
        ret.append((1.0, self.max))
        return ret

    def get_histogram(self, q_points=None):
        """\
        This convenience method gives back an estimated histogram, based
        on quantiles from get_quantiles(). It's mostly just a utility
        for rendering graphs; it's no more accurate than
        get_quantiles(), and probably even less so for very small
        dataset-size-to-bucket-count ratios.

        TODO: Because it stores observations, a ReservoirAccumulator
        could actually give back a real histogram, too.
        """
        ret = []
        qwantz = self.get_quantiles(q_points)
        total_count = self.count
        for sq, eq in zip(qwantz, qwantz[1:]):
            q_range = start_q, end_q = sq[0], eq[0]
            val_range = start_val, end_val = sq[1], eq[1]
            ratio = end_q - start_q
            count = int(ratio * total_count)
            if total_count < len(qwantz):
                if end_val > start_val:
                    count += 1  # not exactly, but sorta.
            else:
                if start_q == 0.0 or end_q == 1.0:
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
        return self._get_quantile(0.50)

    @property
    def quartiles(self):
        gq = self._get_quantile
        return gq(0.25), gq(0.50), gq(0.75)

    @property
    def iqr(self):
        gq = self._get_quantile
        return gq(0.75) - gq(0.25)

    @property
    def trimean(self):
        qs = self.quartiles
        return (qs[0] + (2 * qs[1]) + qs[2]) / 4.0


class ReservoirAccumulator(BaseQuantileAccumulator):
    def __init__(self, data=None, cap=None, q_points=None):
        super(ReservoirAccumulator, self).__init__(q_points=q_points)
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
            super(ReservoirAccumulator, self).add(val)
        else:
            # TODO: randint has a lot of pure-python arg checking
            # machinery we don't need
            idx = random.randint(0, self._count)
            if idx < self._cap:
                self._data[idx] = val
                self._is_sorted = False
                super(ReservoirAccumulator, self).add(val)

    def _get_quantile(self, q=0.5):
        if not (0.0 < q < 1.0):
            raise ValueError('expected a value in range 0.0 - 1.0 (non-inclusive)')
        self._sort()
        data, n = self._data, len(self._data)
        idx = q * (n - 1)
        idx_f, idx_c = int(floor(idx)), int(ceil(idx))
        if idx_f == idx_c:
            return data[idx_f]
        return (data[idx_f] * (idx_c - idx)) + (data[idx_c] * (idx - idx_f))


class P2Accumulator(BaseQuantileAccumulator):
    def __init__(self, data=None, q_points=None):
        super(P2Accumulator, self).__init__(q_points=q_points)
        data = data or []

        self._q_points = P2Estimator._process_q_points(self._q_points)
        self._tmp_acc = ReservoirAccumulator(cap=None)
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
        super(P2Accumulator, self).add(val)

    def get_quantiles(self, q_points=None):
        q_points = q_points or self._q_points
        return super(P2Accumulator, self).get_quantiles(q_points)

    def _get_quantile(self, q):
        try:
            return self._est._get_quantile(q)
        except AttributeError:
            return self._tmp_acc._get_quantile(q)
