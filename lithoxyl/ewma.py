# -*- coding: utf-8 -*-

import math
import time

# 1-, 5-, and 15-minute periods, per Unix load average
DEFAULT_PERIODS = (60, 300, 900)
DEFAULT_INTERVAL = 5


class EWMAAccumulator(object):
    "An exponentially-weighted moving average (EWMA) accumulator"

    def __init__(self, periods=None, interval=None):
        "Takes an iterable of periods and an update interval, both in seconds."
        self._interval = float(interval or DEFAULT_INTERVAL)
        if not self._interval > 0:
            raise ValueError('interval must be greater than 0, not: %r'
                             % self._interval)

        periods = periods or DEFAULT_PERIODS
        self._rate_map = dict([(p, None) for p in periods])
        self._uncounted = 0.0
        self._last_update = time.time()
        self._force_next_update = True

    def add(self, value):
        "Adds a new value to the moving average."
        self._uncounted += value

    def _update(self):
        "Perform the actual decay and reset the counter."
        rate_map = self._rate_map
        cur_time = time.time()
        interval = cur_time - self._last_update

        for period in rate_map:
            new_rate = self._uncounted / interval
            if rate_map[period] is None:
                rate_map[period] = new_rate
            else:
                alpha = 1 - math.exp(-interval / period)
                rate_map[period] += alpha * (new_rate - rate_map[period])
        self._uncounted = 0
        self._last_update = cur_time

    def get_rates(self):
        "Conditionally updates and returns a copy of the rate map"
        if (time.time() - self._last_update) >= self._interval:
            self._update()
        elif self._force_next_update:
            self._force_next_update = False
            self._update()
        return dict(self._rate_map)

    def __repr__(self):
        cn = self.__class__.__name__
        return '<%s rates=%r>' % (cn, self.get_rates())


def _main(incr=1):
    speed_counts = [(0.5, 1), (0.2, 5), (0.5, 10)]
    print_interval = 0.2

    _ewma = EWMAAccumulator(interval=0.1)
    prev_time = prev_print_time = time.time()
    for speed, count in speed_counts:
        i = 0
        while i < count:
            time.sleep(0.05)

            cur_time = time.time()
            dur = cur_time - prev_time
            if dur > speed:
                _ewma.add(incr)
                i += 1
                prev_time = cur_time
            print_dur = cur_time - prev_print_time
            if print_dur > print_interval:
                prev_print_time = cur_time
                print(_ewma.get_rates())


if __name__ == '__main__':
    _main()
