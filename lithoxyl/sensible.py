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
Formatter('{iso8601_time} - {logger_name} - {level_name} - {record_name}')


# name, type, getter(record),

from formatutils import _TYPE_MAP


DEFAULT_FMT_SPEC = {int: 'd',
                    float: 'f',
                    str: 's'}


class FormatField(object):
    def __init__(self, name, type_func, getter, fmt_spec=None):
        self.name = name
        self.type_func = type_func
        self.getter = getter
        self.fmt_spec = fmt_spec or DEFAULT_FMT_SPEC[type_func]
        # TODO: do we need that? -^

        fmt_char = self.fmt_spec[-1:]
        if not issubclass(type_func, _TYPE_MAP[fmt_char]):
            raise TypeError('type mismatch in FormatField %r' % name)


FF = FormatField


FMT_BUILTINS = [FF('logger_name', str, lambda r: r.logger.name),
                FF('logger_id', int, lambda r: id(r.logger)),  # TODO
                FF('record_name', str, lambda r: r.name),
                FF('record_id', int, lambda r: id(r)),  # TODO
                FF('record_status', str, lambda r: r.status),
                FF('record_status_char', str, lambda r: r.status[0].upper()),
                FF('level_name', str, lambda r: r.level),  # TODO
                FF('level_number', float, lambda r: r.level),
                FF('message', str, lambda r: r.message),
                FF('raw_message', str, lambda r: r.message)]  # TODO


BUILTINS = {'logger_name': '',
            'logger_id': '',
            'record_name': '',  # TODO: record_name?
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
