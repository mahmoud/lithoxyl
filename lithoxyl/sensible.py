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


from formatutils import tokenize_format_str


class Formatter(object):
    def __init__(self, format_str, defaults=None, getters=None):
        self.raw_format_str = format_str
        getters = dict(getters or {})
        self.defaults = dict(defaults or {})
        self.field_map = {}
        self.token_chain = []
        self.format_str = ''
        base_fields = tokenize_format_str(format_str)
        for bf in base_fields:
            # TODO: if anonymous and/or positional, raise
            try:
                ff = FMT_BUILTIN_MAP[bf.fname]
            except AttributeError:
                continue
            except KeyError:
                ff = 'TODO'
                raise
                #ff = FormatField(bf.fname, '', '')
            finally:
                self.format_str += str(bf)
            self.field_map[ff.fname] = ff

    def format_record(self, record):
        items = {}
        for fname, field in self.field_map.items():
            try:
                items[fname] = field.getter(record)
            except:
                items[fname] = field.default
        return self.format_str.format(**items)


# Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')


# name, type, getter(record),

from formatutils import _TYPE_MAP, BaseFormatField


DEFAULT_FMT_SPEC = {int: 'd',
                    float: 'f',
                    str: 's'}


class FormatField(BaseFormatField):
    def __init__(self, fname, type_func, getter, fmt_spec=''):
        fmt_spec = fmt_spec or DEFAULT_FMT_SPEC[type_func]
        # TODO: do we need that? -^
        super(FormatField, self).__init__(fname, fmt_spec)
        self.type_func = type_func
        self.getter = getter

        self.default = type_func()  # TODO
        if not issubclass(type_func, _TYPE_MAP[self.type_char]):
            raise TypeError('type mismatch in FormatField %r' % fname)

    def __repr__(self):
        cn = self.__class__.__name__
        return '%s(%r, %r, %r)' % (cn, self.fname, self.type_func, self.getter)


FF = FormatField


# default, fmt_specs
FMT_BUILTINS = [FF('logger_name', str, lambda r: r.logger.name),
                FF('logger_id', int, lambda r: id(r.logger)),  # TODO
                FF('record_name', str, lambda r: r.name),
                FF('record_id', int, lambda r: id(r)),  # TODO
                FF('record_status', str, lambda r: r.status),
                FF('record_status_char', str, lambda r: r.status[0].upper()),
                FF('level_name', str, lambda r: r.level),  # TODO
                FF('level_number', float, lambda r: r.level),
                FF('message', str, lambda r: r.message),
                FF('raw_message', str, lambda r: r.message),  # TODO
                FF('start_timestamp', float, lambda r: r.start_time),
                FF('end_timestamp', float, lambda r: r.end_time),
                FF('start_iso8601', str, lambda r: r),
                FF('end_iso8601', str, lambda r: r),
                FF('duration_secs', float, lambda r: r.duration),
                FF('duration_msecs', float, lambda r: r.duration * 1000.0),
                FF('module_name', str, lambda r: r.callpoint.module_name),
                FF('module_path', str, lambda r: r.callpoint.module_path),
                FF('func_name', str, lambda r: r.callpoint.func_name),
                FF('line_number', int, lambda r: r.callpoint.lineno),
                FF('exc_type', str, lambda r: 'TODO'),
                FF('exc_message', str, lambda r: 'TODO'),
                FF('exc_tb_str', str, lambda r: 'TODO'),
                FF('exc_tb_dict', str, lambda r: 'TODO'),
                FF('process_id', int, lambda r: 'TODO')]


FMT_BUILTIN_MAP = dict([(f.fname, f) for f in FMT_BUILTINS])

'{start_time!iso_8601}'
#Formatter('{userthing:%d} {start_iso8601} - {logger_name} - {record_name}')
forming = Formatter('{start_timestamp} - {logger_name} - {record_name}')

from logger import Record, DEBUG

riker = Record('hello_thomas', DEBUG)

print repr(forming.format_record(riker))


class SensibleSink(object):
    def __init__(self, filters=None, formatter=None, emitter=None):
        pass
