# -*- coding: utf-8 -*-

import os
import random

from moment import MomentAccumulator
from p_squared import QuantileAccumulator, P2QuantileAccumulator
import _statsutils


random.seed(8675309)
test_sets = {'urandom 0-255': [ord(x) for x in os.urandom(16000)],
             'random.random 0.0-1.0': [random.random() for i in xrange(10000)]}


def _assert_round_cmp(a, b, mag=3, name=None):
    thresh = 1.0 / (10 ** mag)
    abs_diff = abs(a - b)
    tmpl = 'round-compare failed at %d digits (%f - %f = %f > %f)'
    rel_diff = (2 * abs_diff) / (a + b)
    err_msg = tmpl % (mag, a, b, rel_diff, thresh)
    if name:
        err_msg = '%r %s' % (name, err_msg)
    assert rel_diff < thresh, err_msg
    return True


def test_momentacc():
    for name, data in test_sets.items():
        ma = MomentAccumulator()
        for v in data:
            ma.add(v)

        for m_name in ('mean', 'variance', 'std_dev', 'skewness', 'kurtosis'):
            ma_val = getattr(ma, m_name)
            ctl_val = getattr(_statsutils, m_name)(data)
            _assert_round_cmp(ctl_val, ma_val, name=m_name)
    return True


def test_quantacc_basic(data=None):
    data = data or range(31)
    qa = QuantileAccumulator()
    for v in data:
        qa.add(v)
    assert qa.median == _statsutils.median(data)
    q1, q2, q3 = qa.quartiles
    assert q1 < q2 < q3
    return True


def test_quantacc():
    for name, data in test_sets.items():
        qa = QuantileAccumulator()
        for v in data:
            qa.add(v)
        assert qa.median == _statsutils.median(data)
        q1, q2, q3 = qa.quartiles
        assert q1 < q2 < q3
        hist = qa.get_histogram()
        assert len(hist) == len(qa._q_points) + 1  # TODO: throwaway test
        #print; import pprint; pprint.pprint(hist)
        #print sum([x.count for x in hist]), 'histogram item count'


def test_p2quantacc():
    for name, data in test_sets.items():
        qa = QuantileAccumulator()
        p2qa = P2QuantileAccumulator()
        for i, v in enumerate(data):
            p2qa.add(v)
            qa.add(v)
            if i and i % 1000 == 0:
                _assert_round_cmp(qa.median,
                                  p2qa.median,
                                  mag=1,
                                  name='%s median' % name)
                print i, qa.median, p2qa.median
        _assert_round_cmp(qa.median,
                          p2qa.median,
                          mag=2,
                          name='%s median' % name)
