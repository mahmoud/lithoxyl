# -*- coding: utf-8 -*-
"""Implements types and functions for rendering
:class:`~lithoxyl.record.Record` instances into strings.
"""
import json

from boltons.formatutils import tokenize_format_str

from lithoxyl.common import EVENTS
from lithoxyl.fields import BUILTIN_FIELD_MAP


__all__ = ['SensibleFormatter', 'SensibleSink']


DEFAULT_QUOTER = json.dumps


class SensibleSink(object):
    def __init__(self, formatter=None, emitter=None, filters=None, on=EVENTS):
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
        if self.filters and not all([f(event) for f in self.filters]):
            return
        entry = self.formatter.on_begin(event)
        return self.emitter.on_begin(event, entry)

    def _on_warn(self, event):
        if self.filters and not all([f(event) for f in self.filters]):
            return
        entry = self.formatter.on_warn(event)
        return self.emitter.on_warn(event, entry)

    def _on_end(self, event):
        if self.filters and not all([f(event) for f in self.filters]):
            return
        entry = self.formatter.on_end(event)
        return self.emitter.on_end(event, entry)

    def _on_comment(self, event):
        if self.filters and not all([f(event) for f in self.filters]):
            return
        entry = self.formatter.on_comment(event)
        return self.emitter.on_comment(event, entry)

    def __repr__(self):
        cn = self.__class__.__name__
        return ('<%s filters=%r formatter=%r emitter=%r>'
                % (cn, self.filters, self.formatter, self.emitter))


class GetterDict(dict):
    """An internal-use-only dict to enable the fetching of values from a
    :class:`~lithoxyl.record.Record`. Tries to fetch a key on a
    record, failing that, tries built-in getters, if that fails,
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


class SensibleEventFormatter(object):
    def __init__(self, base=None, **kwargs):
        defaulter = kwargs.pop('defaulter', None)
        quoter = kwargs.pop('quoter', None)
        extra_fields = kwargs.pop('extra_fields', None)

        self.event_formatters = {}
        for event in EVENTS:
            cur_fmt = kwargs.pop(event, base)
            if not cur_fmt:
                cur_fmt = ''
            rf = SensibleFormatter(cur_fmt, extra_fields=extra_fields,
                                   quoter=quoter, defaulter=defaulter)
            self.event_formatters[event] = rf
        return

    def on_begin(self, begin_event):
        rf = self.event_formatters['begin']
        return rf(begin_event)

    def on_warn(self, warn_event):
        rf = self.event_formatters['warn']
        return rf(warn_event)

    def on_end(self, end_event):
        rf = self.event_formatters['end']
        return rf(end_event)

    def on_comment(self, comment_event):
        rf = self.event_formatters['comment']
        return rf(comment_event)


class SensibleFormatter(object):
    """The basic ``Formatter`` type implements a constrained, but robust,
    microtemplating system rendering Records to strings that are both
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

    >>> from lithoxyl.record import Record
    >>> fmtr = SensibleFormatter('Record status: {status_str}.')
    >>> fmtr.format_record(Record('test').success())
    'Record status: success.'

    Other types of Formatters do not need to inherit from any special
    class. A Formatter is any callable which accepts a Record/mapping,
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

    def format(self, record, *args, **kwargs):
        """Render text, based on the format-string template used to construct
        the object, plus values from the following sources:

          * Positional arguments to this method (``*args``)
          * Keyword arguments to this method (``**kwargs``)
          * Default FormatFields built-in to Lithoxyl
          * Structured data stored in the Record object's ``data_map``

        """
        ret = ''
        kw_vals = GetterDict(record, self._getter_map)
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
