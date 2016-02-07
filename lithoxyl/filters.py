# -*- coding: utf-8 -*-

"""

SensibleLogger has two sinks:

 * (1) statistical (counter or stats aggregator)
 * (1) persistent (stream/file)

For each combination of level and status, choose whether to count or
count+log. The following matrix shows the default log level:

+------------+-------+-------+---------+
|level/status|success|failure|exception|
+------------+-------+-------+---------+
|debug       | count | count |   log   |
+------------+-------+-------+---------+
|info        | count |  log  |   log   |
+------------+-------+-------+---------+
|critical    |  log  |  log  |   log   |
+------------+-------+-------+---------+

Higher verbosity moves the spread of "log" actions diagonally up and
to the left, and lower verbosity, down and to the right.

"""

from common import MAX_LEVEL, LEVEL_ALIAS_MAP


class ThresholdFilter(object):
    def __init__(self, base=None, **kwargs):
        # TODO: filter for warnings?
        # TODO: on-bind lookup behaviors?
        base = LEVEL_ALIAS_MAP[base or MAX_LEVEL]

        self.event_kw_vals = {}
        for event in ('begin', 'success', 'failure', 'exception'):
            level = kwargs.pop(event, base)
            if not level:  # False or explicit None
                level = MAX_LEVEL  # MAX_LEVEL filters all
            level = LEVEL_ALIAS_MAP[level]
            self.event_kw_vals[event] = level

        self.event_thresh_map = dict(self.event_kw_vals)  # TODO
        if kwargs:
            raise TypeError('got unexpected keyword arguments: %r' % kwargs)

    def __call__(self, record):
        try:
            return record.level >= self.event_thresh_map[record.status]
        except KeyError:
            return False
