# -*- coding: utf-8 -*-
"""\

An implementation of P-Squared (Piecewise Parabolic) Quantile
Estimation, which provides efficient online estimation for
quantile-related statistics (e.g., median, quartiles).

For description of the algorithm defined in
http://www.cs.wustl.edu/~jain/papers/ftp/psqr.pdf

Implemented by Kurt Rose and Mahmoud Hashemi.

Copyright 2013, 3-clause BSD License
"""


class P2Estimator(object):
    def __init__(self, q_points, data):
        self._q_points = self._process_q_points(q_points)
        self._q_points = (0.0,) + self._q_points + (1.0,)
        len_data, len_qps = len(data), len(self._q_points)
        if len_data < len_qps:
            msg = ('expected %d or more initial points for '
                   '%d quantiles (got %d)' % (len_qps, len_qps - 2, len_data))
            raise ValueError(msg)

        initial = sorted(data[:len_qps])
        vals = [[i + 1, x] for i, x in enumerate(initial)]
        self._points = pts = zip(self._q_points, vals)
        self._min_point, self._max_point = pts[0][1], pts[-1][1]
        self._lookup = dict(pts)
        self._back_tuples = list(reversed(zip(vals[1:], vals[2:])))

        self._quads = zip(self._q_points[1:], vals, vals[1:], vals[2:])

        for i in xrange(len_qps, len_data):
            self.add(data[i])
        return

    @staticmethod
    def _process_q_points(q_points):
        try:
            qps = sorted([float(x) for x in set(q_points or [])])
            if qps[0] == 0.0:
                qps = qps[1:]
            if qps[-1] == 1.0:
                qps = qps[:-1]
            if not qps or not all([0.0 < x < 1.0 for x in qps]):
                raise ValueError()
        except Exception:
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
        for qpdiv, (ln, lq), cur, (rn, rq) in self._quads:
            cn, cq = cur
            d = int(prev_count * qpdiv + 1 - cn)
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
                else:
                    nq = cq - (lq - cq) / (ln - cn)
            cur[0], cur[1] = cn + d, nq

    def get_quantiles(self):
        return [(x[0], x[1][1]) for x in self._points]

    def _get_quantile(self, q):
        try:
            return self._lookup[float(q)][1]
        except KeyError:
            raise ValueError('quantile not tracked: %r' % q)


def test_random(vals=None, nsamples=100000):
    import random
    import time
    from pprint import pprint
    random.seed(12345)
    qp = (0.01, 0.05, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99)
    if not vals:
        vals = [random.random() for i in range(nsamples)]
    try:
        start = time.time()
        m = P2Estimator(q_points=qp, data=vals)
        p = m.get_quantiles()
        duration = time.time() - start
        tmpl = ("P2Estimator processed %d measurements "
                "in %f seconds (%f ms each)")
        pprint(p)
        print tmpl % (nsamples, duration, 1000 * duration / nsamples)
    except Exception:
        import traceback
        import pdb
        traceback.print_exc()
        pdb.post_mortem()
        raise
    for k, v in p:
        if not k:
            continue
        if not 0.95 < v / k < 1.05:
            print "problem: %s is %s, should be ~%s" % (k, v, k)
    return


if __name__ == "__main__":
    test_random()
