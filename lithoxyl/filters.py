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

from common import MAX_LEVEL


class ThresholdFilter(object):
    def __init__(self, **kwargs):
        # TODO: filter for warnings?
        # TODO: on-bind lookup behaviors?
        # TODO: add "default" response?
        self.event_kw_vals = {}
        for event in ('begin', 'success', 'failure', 'exception'):
            self.event_kw_vals[event] = kwargs.pop(event, MAX_LEVEL)

        self.event_thresh_map = dict(self.event_kw_vals)  # TODO
        if kwargs:
            raise TypeError('got unexpected keyword arguments: %r' % kwargs)

    def __call__(self, record):
        try:
            return record.level >= self.event_thresh_map[record.status]
        except KeyError:
            return False
