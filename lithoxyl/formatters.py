# -*- coding: utf-8 -*-

import time
import datetime
from json import dumps as escape_str

from tzutils import UTC, LocalTZ
from formatutils import tokenize_format_str, BaseFormatField


def timestamp2iso8601_noms(timestamp, local=False):
    """
    with time.strftime(), one would have to do fractional
    seconds/milliseconds manually, because the timetuple used doesn't
    include data necessary to support the %f flag.

    This function is about twice as fast as datetime.strftime(),
    however. That's nothing compared to time.time()
    vs. datetime.now(), which is two orders of magnitude faster.
    """
    tformat = '%Y-%m-%d %H:%M:%S'
    if local:
        tstruct = time.localtime(timestamp)
    else:
        tstruct = time.gmtime(timestamp)
    return time.strftime(tformat, tstruct)


def timestamp2iso8601(timestamp, local=False, tformat=None):
    tformat = tformat or '%Y-%m-%d %H:%M:%S.%f%z'
    if local:
        dt = datetime.datetime.fromtimestamp(timestamp, tz=LocalTZ)
    else:
        dt = datetime.datetime.fromtimestamp(timestamp, tz=UTC)
    return dt.isoformat(' ')


class FormatField(BaseFormatField):
    def __init__(self, fname, fspec, getter=None, default=None, quote=None):
        super(FormatField, self).__init__(fname, fspec)
        self.default = default
        self.getter = getter
        if quote is None:
            numeric = issubclass(self.type_func, (int, float))
            quote = not numeric
        self.quote = quote

# default, fmt_specs
FF = FormatField
FMT_BUILTINS = [FF('logger_name', 's', lambda r: r.logger.name),
                FF('logger_id', 'd', lambda r: id(r.logger)),  # TODO
                FF('record_name', 's', lambda r: r.name),
                FF('record_id', 'd', lambda r: id(r)),  # TODO
                FF('record_status', 's', lambda r: r.status, quote=False),
                FF('record_status_char', 's', lambda r: r.status_char, quote=False),
                FF('record_warn_char', 's', lambda r: 'W' if r.warnings else ' ', quote=False),
                FF('level_name', 's', lambda r: r.level),  # TODO
                FF('level_number', 'd', lambda r: r.level),
                FF('message', 's', lambda r: r.message),
                FF('raw_message', 's', lambda r: r.raw_message),
                FF('begin_timestamp', '.14g', lambda r: r.begin_time),
                FF('end_timestamp', '.14g', lambda r: r.end_time),
                FF('begin_iso8601', 's', lambda r: timestamp2iso8601(r.begin_time)),
                FF('end_iso8601', 's', lambda r: timestamp2iso8601(r.end_time)),
                FF('begin_local_iso8601', 's', lambda r: timestamp2iso8601(r.begin_time, local=True)),
                FF('end_local_iso8601', 's', lambda r: timestamp2iso8601(r.end_time, local=True)),
                FF('duration_secs', '.3f', lambda r: r.duration),
                FF('duration_msecs', '.3f', lambda r: r.duration * 1000.0),
                FF('module_name', 's', lambda r: r.callpoint.module_name),
                FF('module_path', 's', lambda r: r.callpoint.module_path),
                FF('func_name', 's', lambda r: r.callpoint.func_name),
                FF('line_number', 'd', lambda r: r.callpoint.lineno),
                FF('exc_type', 's', lambda r: 'TODO'),
                FF('exc_message', 's', lambda r: 'TODO'),
                FF('exc_tb_str', 's', lambda r: 'TODO'),
                FF('exc_tb_dict', 's', lambda r: 'TODO'),
                FF('process_id', 'd', lambda r: 'TODO')]


FMT_BUILTIN_MAP = dict([(f.fname, f) for f in FMT_BUILTINS])
BUILTIN_GETTERS = dict([(f.fname, f.getter) for f in FMT_BUILTINS])
BUILTIN_QUOTERS = set([f.fname for f in FMT_BUILTINS if f.quote])


class LazyExtrasDict(dict):
    def __init__(self, record, getters):
        self.record = record
        self.getters = getters

    def __missing__(self, key):
        getter = self.getters[key]
        return getter(self.record)


class Templette(object):

    getters = BUILTIN_GETTERS

    def __init__(self, tmpl_str, quoter=None, defaulter=None):
        self.defaulter = defaulter or (lambda t: str(t))
        if not callable(self.defaulter):
            raise TypeError()
        self.quoter = quoter or self._default_quoter
        if not callable(self.quoter):
            raise TypeError()
        # self.getters = getters  # dict, handled at class level now

        self.raw_tmpl_str = tmpl_str
        self.tokens = tokenize_format_str(tmpl_str)
        self.default_map = {}
        self.quote_map = {}
        for t in self.tokens:
            if hasattr(t, 'base_name'):
                self.default_map[t] = self.defaulter(t)
                self.quote_map[t] = self.quoter(t)

    def format_record(self, record, *args, **kwargs):
        ret = ''
        kw_vals = LazyExtrasDict(record, self.getters)
        kw_vals.update(kwargs)
        for t in self.tokens:
            try:
                name = t.base_name
            except AttributeError:
                ret += t
                continue
            try:
                if t.is_positional:
                    seg = t.fstr.format(*args)
                else:
                    seg = t.fstr.format(**{name: kw_vals[name]})
                if self.quote_map[t]:
                    seg = escape_str(seg)
                ret += seg
            except:
                ret += self.default_map[t]
        return ret

    @staticmethod
    def _default_quoter(token):
        return token.fname in BUILTIN_QUOTERS

    __call__ = format_record


class Formatter(object):
    # TODO: inherit from templette?

    def __init__(self, format_str):
        self.templette = Templette(format_str)
        # TODO: check that templette complies with reversability
        # requirements
        # TODO: check field type compatibilty when
        # default format specs have been overridden for built-in
        # format fields

    def format_record(self, record):
        try:
            return self.templette.format_record(record)
        except:
            # TODO: basically impossible atm, but eventually log to
            # stderr or something
            raise

    __call__ = format_record


"""
reversability requirements:

all fields must be one or more of:

* known, fixed length
  (standard for single character fields, certain numeric fields maybe)
* unquoted but whitespace-free and not adjacent to any other unquoted field
  (standard for numbers and certain fixed-set labels)
* quoted, escaped
  (standard for longer strings that might contain whitespace)
"""
