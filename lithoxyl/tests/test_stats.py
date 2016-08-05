# -*- coding: utf-8 -*-

import os
import random

from lithoxyl.moment import MomentAccumulator
from lithoxyl.quantile import ReservoirAccumulator, P2Accumulator
import _statsutils


random.seed(8675309)
test_sets = {'urandom 0-255': [ord(x) for x in os.urandom(16000)],
             'random.random 0.0-1.0': [random.random() for i in xrange(100000)]}


def _assert_round_cmp(a, b, mag=3, name=None):
    thresh = 1.0 / (10 ** mag)
    abs_diff = round(abs(a - b), mag + 1)
    tmpl = 'round-compare failed at %d digits (%f - %f = %f > %f)'
    rel_diff = (2 * abs_diff) / (a + b)
    err_msg = tmpl % (mag, a, b, abs_diff, thresh)
    if name:
        err_msg = '%r %s' % (name, err_msg)
    assert rel_diff < thresh, err_msg
    return True


def test_momentacc_basic():
    for name, data in test_sets.items():
        ma = MomentAccumulator()
        for v in data:
            ma.add(v)

        for m_name in ('mean', 'variance', 'std_dev', 'skewness', 'kurtosis'):
            ma_val = getattr(ma, m_name)
            ctl_val = getattr(_statsutils, m_name)(data)
            _assert_round_cmp(ctl_val, ma_val, mag=4, name=m_name)
    return True


def test_momentacc_norm():
    ma = MomentAccumulator()
    for v in [random.gauss(10, 4) for i in xrange(5000)]:
        ma.add(v)
    _assert_round_cmp(10, abs(ma.mean), mag=1)
    _assert_round_cmp(4, ma.std_dev, mag=1)
    _assert_round_cmp(0, ma.skewness, mag=1)
    _assert_round_cmp(3, ma.kurtosis, mag=1)


def test_quantacc_basic(data=None):
    data = data or range(31)
    qa = ReservoirAccumulator()
    for v in data:
        qa.add(v)
    assert qa.median == _statsutils.median(data)
    q1, q2, q3 = qa.quartiles
    assert q1 < q2 < q3
    return True


def test_quantacc():
    for name, data in test_sets.items():
        qa = ReservoirAccumulator()
        for v in data:
            qa.add(v)
        _assert_round_cmp(qa.median, _statsutils.median(data), mag=6)
        q1, q2, q3 = qa.quartiles
        assert q1 < q2 < q3
        hist = qa.get_histogram()
        assert hist
        #print; import pprint; pprint.pprint(hist)
        #print sum([x.count for x in hist]), 'histogram item count'


def test_p2quantacc():
    for name, data in test_sets.items():
        qa = ReservoirAccumulator()
        p2qa = P2Accumulator()
        for i, v in enumerate(data):
            p2qa.add(v)
            qa.add(v)
            if i and i % 1000 == 0:
                _assert_round_cmp(qa.median,
                                  p2qa.median,
                                  mag=1,
                                  name='%s median' % name)
                #print i, qa.median, p2qa.median

        _assert_round_cmp(qa.median,
                          p2qa.median,
                          mag=2,
                          name='%s median' % name)


def test_acc_random():
    data = test_sets['random.random 0.0-1.0']

    qa = ReservoirAccumulator(data)
    capqa = ReservoirAccumulator(data, cap=True)
    p2qa = P2Accumulator(data)
    for acc in (qa, capqa, p2qa):
        for qp, v in acc.get_quantiles():
            if qp > 0:
                assert 0.95 < (v / qp) < 1.05
