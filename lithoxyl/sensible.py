# -*- coding: utf-8 -*-
"""Implements types and functions for rendering
:class:`~lithoxyl.action.Action` instances into strings.
"""

import os
import time
import json
import socket
import datetime

from boltons.timeutils import UTC, LocalTZ
from boltons.formatutils import BaseFormatField
from boltons.formatutils import tokenize_format_str

from lithoxyl.common import EVENTS, IMPORT_TIME, MAX_LEVEL, get_level


__all__ = ['SensibleFormatter', 'SensibleSink']


DEFAULT_QUOTER = json.dumps

FIELD_MAP = {}
BUILTIN_FIELD_MAP = {}  # populated below


def register_builtin_field(field):
    register_field(field)
    BUILTIN_FIELD_MAP[field.fname] = field


def register_field(field):
    FIELD_MAP[field.fname] = field


class SensibleSink(object):
    def __init__(self, formatter=None, emitter=None, filters=None, on=EVENTS):
        # TODO: get_level for this
        events = on
        if isinstance(events, basestring):
            events = [events]
        unknown_events = [e for e in events if e not in EVENTS]
        if unknown_events:
            raise ValueError('unrecognized events: %r (must be one of %r)'
                             % (unknown_events, EVENTS))

        self._events = [e.lower() for e in events]
        self.filters = list(filters or [])
        self.formatter = formatter
        self.emitter = emitter

        if 'begin' in self._events:
            self.on_begin = self._on_begin
        if 'warn' in self._events:
            self.on_warn = self._on_warn
        if 'end' in self._events:
            self.on_end = self._on_end
        if 'comment' in self._events:
            self.on_comment = self._on_comment

    def _on_begin(self, event):
        if self.filters and not all([f.on_begin(event) for f in self.filters]):
            return
        entry = self.formatter.on_begin(event)
        return self.emitter.on_begin(event, entry)

    def _on_warn(self, event):
        if self.filters and not all([f.on_warn(event) for f in self.filters]):
            return
        entry = self.formatter.on_warn(event)
        return self.emitter.on_warn(event, entry)

    def _on_end(self, event):
        if self.filters and not all([f.on_end(event) for f in self.filters]):
            return
        entry = self.formatter.on_end(event)
        return self.emitter.on_end(event, entry)

    def _on_comment(self, event):
        if self.filters and not all([f.on_comment(event)
                                     for f in self.filters]):
            return
        entry = self.formatter.on_comment(event)
        return self.emitter.on_comment(event, entry)

    def __repr__(self):
        cn = self.__class__.__name__
        return ('<%s filters=%r formatter=%r emitter=%r>'
                % (cn, self.filters, self.formatter, self.emitter))


class SensibleFilter(object):
    def __init__(self, base=None, **kw):
        # TODO: on-bind lookup behaviors?

        base = get_level(base or MAX_LEVEL)

        self.begin_level = get_level(kw.pop('begin', base) or MAX_LEVEL)
        self.success_level = get_level(kw.pop('success', base) or MAX_LEVEL)
        self.failure_level = get_level(kw.pop('failure', base) or MAX_LEVEL)
        self.exception_level = get_level(kw.pop('exception', base)
                                         or MAX_LEVEL)
        self.warn_level = get_level(kw.pop('warn', base) or MAX_LEVEL)
        self.block_comments = kw.pop('block_comments', False)
        self.verbose_check = kw.pop('verbose_check', None)
        if not self.verbose_check:
            verbose_flag = kw.pop('verbose_flag', 'verbose')
            self.verbose_check = lambda e: e.action.data_map.get(verbose_flag)

        if kw:
            raise TypeError('got unexpected keyword arguments: %r' % kw)

    def on_begin(self, ev):
        if ev.action.level >= self.begin_level:
            return True
        elif self.verbose_check and self.verbose_check(ev):
            return True
        return False

    def on_end(self, ev):
        ret, act, status = False, ev.action, ev.status
        if status == 'success':
            ret = act.level >= self.success_level
        elif status == 'failure':
            ret = act.level >= self.failure_level
        elif status == 'exception':
            ret = act.level >= self.exception_level
        if not ret:
            if self.verbose_check and self.verbose_check(ev):
                ret = True
        return ret

    def on_warn(self, ev):
        if ev.action.level >= self.warn_level:
            return True
        elif self.verbose_check and self.verbose_check(ev):
            return True
        return False

    def on_comment(self, ev):
        return not self.block_comments


class GetterDict(dict):
    """An internal-use-only dict to enable the fetching of values from a
    :class:`~lithoxyl.action.Action`. Tries to fetch a key on a
    action, failing that, tries built-in getters, if that fails,
    returns ``None``. Exceptions raised from getters are not caught
    here.
    """
    def __init__(self, wrapped, getters):
        self.wrapped = wrapped
        self.getters = getters

    def __missing__(self, key):
        try:
            return self.wrapped[key]
        except KeyError:
            try:
                return self.getters[key](self.wrapped)
            except KeyError:
                pass
        return None


class SensibleFormatter(object):
    def __init__(self, base=None, **kwargs):
        defaulter = kwargs.pop('defaulter', None)
        quoter = kwargs.pop('quoter', None)
        extra_fields = kwargs.pop('extra_fields', None)

        for event in EVENTS:
            cur_fmt = kwargs.pop(event, base)
            if not cur_fmt:
                cur_fmt = ''
            rf = SensibleMessageFormatter(cur_fmt, extra_fields=extra_fields,
                                          quoter=quoter, defaulter=defaulter)
            setattr(self, '_' + event + '_formatter', rf)
        return

    def on_begin(self, begin_event):
        return self._begin_formatter(begin_event)

    def on_warn(self, warn_event):
        return self._warn_formatter(warn_event)

    def on_end(self, end_event):
        return self._end_formatter(end_event)

    def on_comment(self, comment_event):
        return self._comment_formatter(comment_event)


class SensibleMessageFormatter(object):
    """The basic ``Formatter`` type implements a constrained, but robust,
    microtemplating system rendering Actions to strings that are both
    human-readable *and* machine-readable. This system is based on
    :class:`FormatFields <lithoxyl.fields.FormatField>`, many of which
    are built-in.

    Args:
        format_str (str): The template for the string to be rendered,
            e.g., ``"Request outcome: {status_str}"``.
        extra_fields (dict): Optionally specify a map of fields this
            Formatter should recognize in addition to the builtins.
        quoter (callable): Optionally override the default quoting
            function.
        defaulter (callable): Optionally override how the Formatter
            determines the default value for fields.

    Generally a Formatter is called only with the template string.

    >>> from lithoxyl.action import Action
    >>> fmtr = SensibleFormatter('Action status: {status_str}.')
    >>> fmtr.format_action(Action('test').success())
    'Action status: success.'

    Other types of Formatters do not need to inherit from any special
    class. A Formatter is any callable which accepts a Action/mapping,
    ``*args``, and ``**kwargs``, and returns text.
    """
    def __init__(self, format_str, **kwargs):
        extra_fields = kwargs.pop('extra_fields', None)
        quoter = kwargs.pop('quoter', None)
        defaulter = kwargs.pop('defaulter', None)
        if kwargs:
            raise TypeError('unexpected keyword arguments: %r' % kwargs.keys())
        if quoter is False:
            # disable quoting
            self.quoter = lambda field: None
        else:
            self.quoter = quoter or self._default_quoter
        if not callable(self.quoter):
            raise TypeError('expected callable or False for quoter,'
                            ' not %r' % self.quoter)
        self.defaulter = defaulter or self._default_defaulter
        if not callable(self.defaulter):
            raise TypeError('expected callable for defaulter, not %r'
                            % self.defaulter)

        self._field_map = dict(BUILTIN_FIELD_MAP)
        if extra_fields:
            extra_field_map = dict([(f.fname, f) for f in extra_fields or []])
            self._field_map.update(extra_field_map)
        self._getter_map = dict([(f.fname, f.getter)
                                 for f in self._field_map.values()])

        self.raw_format_str = format_str
        self.tokens = tokenize_format_str(format_str)
        self.default_map = {}
        self.quoter_map = {}
        for token in self.tokens:
            try:
                fspec = token.fspec
            except AttributeError:
                # not a field, just a string constant
                continue
            try:
                self.default_map[token] = self.defaulter(token)
                self.quoter_map[token] = self.quoter(token)
                if not fspec:
                    token.set_fspec(self._field_map[token.fname].fspec)
            except KeyError:
                # not a builtin field
                pass
        return

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.raw_format_str)

    def format(self, event, *args, **kwargs):
        """Render text, based on the format-string template used to construct
        the object, plus values from the following sources:

          * Positional arguments to this method (``*args``)
          * Keyword arguments to this method (``**kwargs``)
          * Default FormatFields built-in to Lithoxyl
          * Structured data stored in the Action object's ``data_map``

        """
        ret = ''
        kw_vals = GetterDict(event, self._getter_map)
        kw_vals.update(kwargs)
        q_map, d_map = self.quoter_map, self.default_map
        for t in self.tokens:
            try:
                name = t.base_name
            except AttributeError:
                ret += t  # just a string segment, moving on
                continue
            try:
                if t.is_positional:
                    seg = t.fstr.format(*args)
                else:
                    seg = t.fstr.format(**{name: kw_vals[name]})
                if q_map[t]:
                    seg = q_map[t](seg)
                ret += seg
            except Exception:
                ret += d_map[t]
        return ret

    def _default_defaulter(self, token):
        return str(token)

    def _default_quoter(self, token):
        field = self._field_map.get(token.fname)
        # if it's not a builtin field, we quote it by default
        if not field or field.quote:
            return DEFAULT_QUOTER
        else:
            return None

    __call__ = format


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

# Fields follow

"""Lithoxyl comes with many built-in format *fields* meant to be used
with the standard :class:`~lithoxyl.logger.Logger` and
:class:`~lithoxyl.action.Action`. Sinks can take advantage of these
with the :class:`~lithoxyl.sensible.SensibleFormatter` type or subtypes.
"""
# NOTE: docstring table needs slashes double escaped. Also, newline
# literals "\n" removed.

# TODO: exc_repr field


def timestamp2iso8601_noms(timestamp, local=False, with_tz=True):
    """
    with time.strftime(), one would have to do fractional
    seconds/milliseconds manually, because the timetuple used doesn't
    include data necessary to support the %f flag.

    This function is about twice as fast as datetime.strftime(),
    however. That's nothing compared to time.time()
    vs. datetime.now(), which is two orders of magnitude faster.
    """
    if with_tz:
        tformat = '%Y-%m-%dT%H:%M:%S %Z'
    else:
        tformat = '%Y-%m-%dT%H:%M:%S'
    if local:
        tstruct = time.localtime(timestamp)
    else:
        tstruct = time.gmtime(timestamp)
    return time.strftime(tformat, tstruct)


def timestamp2iso8601(timestamp, local=False, with_tz=True, tformat=None):
    if with_tz:
        tformat = tformat or '%Y-%m-%dT%H:%M:%S.%f%z'
    else:
        tformat = tformat or '%Y-%m-%dT%H:%M:%S.%f'
    if local:
        dt = datetime.datetime.fromtimestamp(timestamp, tz=LocalTZ)
    else:
        dt = datetime.datetime.fromtimestamp(timestamp, tz=UTC)
    return dt.strftime(tformat)


class SensibleField(BaseFormatField):
    """Fields specify whether or not they should be *quoted* (i.e.,
    whether or not values will contain whitespace or other
    delimiters), but not the exact method for their quoting. That
    aspect is reserved for the Formatter.
    """
    def __init__(self, fname, fspec='s', getter=None, **kwargs):
        quote = kwargs.pop('quote', None)
        if kwargs:
            raise TypeError('unexpected keyword arguments: %r' % kwargs.keys())
        super(SensibleField, self).__init__(fname, fspec)
        self.getter = getter
        if quote is None:
            # numeric fields should appear without quotes
            numeric = issubclass(self.type_func, (int, float))
            quote = not numeric
        self.quote = quote


def duration_auto(event):
    duration = event.action.duration
    if duration < 0.001:
        return '%.3fus' % (duration * 1e6)
    if duration < 1.0:
        return '%.3fms' % (duration * 1e3)
    return '%.4fs' % duration


# default, fmt_specs
_SF = SensibleField
BASIC_FIELDS = [_SF('logger_name', 's', lambda e: e.action.logger.name),
                _SF('logger_id', 'd', lambda e: e.action.logger.logger_id),
                _SF('action_name', 's', lambda e: e.action.name),
                _SF('action_id', 'd', lambda e: e.action_id),
                _SF('action_guid', 's', lambda e: e.action.guid, quote=False),
                _SF('status_str', 's', lambda e: e.status, quote=False),
                _SF('status_char', 's', lambda e: e.status_char, quote=False),
                _SF('warn_char', 's', lambda e: e.warn_char, quote=False),  # TODO
                _SF('level_name', 's', lambda e: e.level_name, quote=False),
                _SF('level_name_upper', 's', lambda e: e.action.level_name.upper(), quote=False),
                _SF('level_char', 's', lambda e: e.action.level_name.upper()[0], quote=False),
                _SF('level_number', 'd', lambda e: e.level._value),
                _SF('data_map', 's', lambda e: json.dumps(e.action.data_map, sort_keys=True), quote=False),
                _SF('data_map_repr', 's', lambda e: repr(e.action.data_map), quote=False),
                _SF('begin_message', 's', lambda e: e.begin_event.message),
                _SF('begin_message_raw', 's', lambda e: e.begin_event.raw_message),
                _SF('end_message', 's', lambda e: e.action.end_event.message),
                _SF('end_message_raw', 's', lambda e: e.action.end_event.raw_message),
                _SF('event_message', 's', lambda e: e.message),
                _SF('event_message_raw', 's', lambda e: e.message),
                _SF('begin_timestamp', '.14g', lambda e: e.action.begin_event.etime),
                _SF('end_timestamp', '.14g', lambda e: e.action.end_event.etime),
                _SF('duration_s', '.3f', lambda e: e.action.duration),
                _SF('duration_ms', '.3f', lambda e: e.action.duration * 1e3),
                _SF('duration_us', '.3f', lambda e: e.action.duration * 1e6),
                _SF('duration_auto', '>9s', duration_auto, quote=False),
                _SF('module_name', 's', lambda e: e.callpoint.module_name),
                _SF('module_path', 's', lambda e: e.callpoint.module_path),
                _SF('func_name', 's', lambda e: e.callpoint.func_name, quote=False),
                _SF('line_number', 'd', lambda e: e.callpoint.lineno),
                _SF('exc_type', 's', lambda e: e.action.exc_event.exc_info.exc_type, quote=False),
                _SF('exc_message', 's', lambda e: e.action.exc_event.exc_info.exc_msg),
                _SF('exc_tb_str', 's', lambda e: str(e.action.exc_event.exc_info.tb_info)),
                _SF('exc_tb_list', 's', lambda e: e.action.exc_event.exc_info.tb_info.frames),
                _SF('process_id', 'd', lambda e: os.getpid())]

# ISO8601 and variants. combinations of:
#   * begin/end
#   * UTC/Local
#   * with/without milliseconds
#   * with/without timezone (_noms variants have textual timezone)
ISO8601_FIELDS = [
    _SF('iso_begin', 's',
        lambda e: timestamp2iso8601(e.action.begin_event.etime)),
    _SF('iso_end', 's',
        lambda e: timestamp2iso8601(e.action.end_event.etime)),
    _SF('iso_begin_notz', 's',
        lambda e: timestamp2iso8601(e.action.begin_event.etime,
                                    with_tz=False)),
    _SF('iso_end_notz', 's',
        lambda e: timestamp2iso8601(e.action.end_event.etime,
                                    with_tz=False)),
    _SF('iso_begin_local', 's',
        lambda e: timestamp2iso8601(e.action.begin_event.etime,
                                    local=True)),
    _SF('iso_end_local', 's',
        lambda e: timestamp2iso8601(e.action.end_event.etime,
                                    local=True)),
    _SF('iso_begin_local_notz', 's',
        lambda e: timestamp2iso8601(e.action.begin_event.etime,
                                    local=True, with_tz=False)),
    _SF('iso_end_local_notz', 's',
        lambda e: timestamp2iso8601(e.action.end_event.etime,
                                    local=True, with_tz=False)),
    _SF('iso_begin_local_noms', 's',
        lambda e: timestamp2iso8601_noms(e.action.begin_event.etime,
                                         local=True)),
    _SF('iso_end_local_noms', 's',
        lambda e: timestamp2iso8601_noms(e.action.end_event.etime,
                                         local=True)),
    _SF('iso_begin_local_noms_notz', 's',
        lambda e: timestamp2iso8601_noms(e.action.begin_event.etime,
                                         local=True, with_tz=False)),
    _SF('iso_end_local_noms_notz', 's',
        lambda e: timestamp2iso8601_noms(e.action.end_event.etime,
                                         local=True, with_tz=False))]

# using the T separator means no whitespace and thus no quoting
for f in ISO8601_FIELDS:
    f.quote = False


DELTA_FIELDS = [
    _SF('import_delta_s', '0.6f', lambda e: e.etime - IMPORT_TIME),
    _SF('import_delta_ms', '0.4f', lambda e: (e.etime - IMPORT_TIME) * 1000)]


PARENT_DEPTH_INDENT = '   '


PARENT_FIELDS = [
    _SF('parent_depth', 'd', lambda e: e.action.parent_depth),
    _SF('parent_depth_indent', 's',
        lambda e: e.action.parent_depth * PARENT_DEPTH_INDENT,
        quote=False)]


for f in BASIC_FIELDS:
    register_builtin_field(f)
for f in PARENT_FIELDS:
    register_builtin_field(f)
for f in ISO8601_FIELDS:
    register_builtin_field(f)
for f in DELTA_FIELDS:
    register_builtin_field(f)

del f
