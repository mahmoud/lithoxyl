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


class ThresholdFilter(object):
    def __init__(self, **kwargs):
        # TODO: filter for warnings?
        # TODO: on-bind lookup behaviors?
        # TODO: add "default" response?
        self.event_kw_vals = {}
        for event in ('start', 'success', 'failure', 'exception'):
            self.event_kw_vals[event] = kwargs.pop(event, 0)

        self.event_thresh_map = dict(self.event_kw_vals)  # TODO
        if kwargs:
            raise TypeError('got unexpected keyword arguments: %r' % kwargs)

    def __call__(self, record):
        try:
            return record.level >= self.event_thresh_map[record.status]
        except KeyError:
            return False


class Formatter(object):
    def __init__(self, format_str, defaults):
        self.raw_format_str = format_str
        self.defaults = dict(defaults)


Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
Formatter('{iso8601_time} - {logger_name} - {level_name} - {record_type}')


BUILTINS = {'logger_name': '',
            'logger_id': '',
            'record_type': '',  # TODO: record_name?
            'record_id': '',
            'record_status': '',
            'level_name': '',
            'level_number': '',
            'message': '',
            'raw_message': '',
            'start_timestamp': '',
            'end_timestamp': '',
            'start_iso8601': '',
            'end_iso8601': '',
            'duration_secs': '',
            'duration_msecs': '',
            'module_name': '',
            'module_path': '',
            'func_name': '',
            'line_number': '',
            'exc_type': '',
            'exc_message': '',
            'exc_tb_str': '',
            'exc_tb_dict': '',
            'process_id': ''}  # TODO: pid?





class SensibleSink(object):
    def __init__(self, filters=None, formatter=None, emitter=None):
        pass