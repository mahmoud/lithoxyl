# -*- coding: utf-8 -*-


class MomentAccumulator(object):
    """\
    An accumulator for tracking statistical moments. Supports
    arithmetic mean, variance, standard deviation, and the
    distribution shape-related moments, skewness and kurtosis.

    It operates using online approaches, and does not store
    observations. As a result, it uses a more-or-less fixed amount of
    memory, but has a higher insertion cost. Also, because this is
    using simple Python doubles, it is likely to build up a good
    amount of floating point drift. If that's not good enough, use an
    accumulator that stores observations, make a Decimal version, or
    use NumPy, I guess.

    Almost called it the KodakAccumulator, but trademarks, bad jokes,
    etc.

    N.B. For convenience, values default to -0.0 when initially
    uncomputable, such as mean when there is no data, or variance when
    there's only one data point. I would use NaN, but in Python (2 and
    3), NaN's repr() does not round-trip. I might revisit this
    interface optimization later.
    """
    def __init__(self):
        self._count = 0
        self._min = float('inf')
        self._max = float('-inf')
        self._mean = -0.0
        self._m2 = -0.0
        self._m3 = -0.0
        self._m4 = -0.0

    def add(self, val):
        # TODO: keep max/min? not strictly necessary here.
        if val > self._max:
            self._max = val
            if self._count == 0:
                self._min = val
        elif val < self._min:
            self._min = val

        self._count += 1
        n, m2, m3, m4 = self._count, self._m2, self._m3, self._m4
        delta = val - self._mean
        delta_n = delta / n
        delta_n2 = delta_n ** 2
        term = delta * delta_n * (n - 1)
        self._mean = self._mean + delta_n
        self._m4 = (m4 +
                    term * delta_n2 * (n ** 2 - 3 * n + 3) +
                    6 * delta_n2 * m2 -
                    4 * delta_n * m3)
        self._m3 = (m3 +
                    term * delta_n * (n - 2) -
                    3 * delta_n * m2)
        self._m2 = m2 + term

    @property
    def count(self):
        return self._count

    @property
    def mean(self):
        return self._mean

    @property
    def variance(self):
        try:
            return self._m2 / (self._count - 1)
        except ArithmeticError:
            return -0.0

    @property
    def skewness(self):
        try:
            return ((self._count ** 0.5) * self._m3) / (self._m2 ** 1.5)
        except ArithmeticError:
            return -0.0

    @property
    def kurtosis(self):
        # TODO: subtract 3? (for normal curve = 0)
        try:
            return (self._count * self._m4) / (self._m2 ** 2)
        except ArithmeticError:
            return -0.0

    @property
    def std_dev(self):
        return self.variance ** 0.5
