# -*- coding: utf-8 -*-
"""Implements types and functions for rendering
:class:`~lithoxyl.record.Record` instances into strings.
"""
import json

from common import EVENTS
from fields import BUILTIN_FIELD_MAP
from formatutils import tokenize_format_str

DEFAULT_QUOTER = json.dumps


__all__ = ['Formatter']


class LazyExtrasDict(dict):
    """An internal-use-only dict to enable the fetching of values from a
    :class:`~lithoxyl.record.Record`. First, attempts to use a
    "getter" as defined in the map of known format fields,
    *getters*. Most of those fields simply access an attribute on the
    Record instance. If no such getter exists, assume that the desired
    key is expected to be in the *extras* dict of the target Record.

    If the key is neither a known "getter" or "extra", ``None`` is
    returned. Exceptions raised from getters are not caught.
    """
    # TODO: typos in field names will result in None
    def __init__(self, record, getters):
        self.record = record
        self.getters = getters

    def __missing__(self, key):
        try:
            getter = self.getters[key]
        except KeyError:
            return self.record.extras.get(key)
        else:
            return getter(self.record)


class Formatter(object):
    def __init__(self, base=None, **kwargs):
        defaulter = kwargs.pop('defaulter', None)
        quoter = kwargs.pop('quoter', None)
        extra_fields = kwargs.pop('extra_fields', None)

        self.event_formatters = {}
        for event in EVENTS:
            cur_fmt = kwargs.pop(event, base)
            if not cur_fmt:
                cur_fmt = ''
            rf = RecordFormatter(cur_fmt, extra_fields=extra_fields,
                                 quoter=quoter, defaulter=defaulter)
            self.event_formatters[event] = rf
        return

    def on_begin(self, begin_record):
        rf = self.event_formatters['begin']
        return rf(begin_record)

    def on_warn(self, warn_record):
        rf = self.event_formatters['warn']
        return rf(warn_record)

    def on_complete(self, complete_record):
        rf = self.event_formatters['complete']
        return rf(complete_record)


class RecordFormatter(object):
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
    >>> fmtr = Formatter('Record status: {status_str}.')
    >>> fmtr.format_record(Record('test').success())
    'Record status: success.'

    Other types of Formatters do not need to inherit from
    ``Formatter``, they just need to implement the
    :meth:`Formatter.format_record` method.

    .. TODO: decide whether Formatters should be callable or implement .format_record
    .. TODO: links to built-in fields

    """
    def __init__(self, format_str,
                 extra_fields=None, quoter=None, defaulter=None):
        self.defaulter = defaulter or self._default_defaulter
        if not callable(self.defaulter):
            raise TypeError('expected callable for Formatter.defaulter, not %r'
                            % self.defaulter)
        if quoter is False:
            # disable quoting
            self.quoter = lambda field: None
        else:
            self.quoter = quoter or self._default_quoter
        if not callable(self.quoter):
            raise TypeError('expected callable or False for Formatter.quoter,'
                            ' not %r' % self.quoter)

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

    def format_record(self, record, *args, **kwargs):
        """
        Render a :class:`~lithoxyl.record.Record` into text, using values from the following sources:

          * Positional arguments to this method (``*args``)
          * Keyword arguments to this method (``**kwargs``)
          * FormatFields built-in to Lithoxyl
          * Structured data stored in the Record object's ``extras`` map

        .. TODO: adjust the above list to account for overriding behavior
        """
        ret = ''
        kw_vals = LazyExtrasDict(record, self._getter_map)
        kw_vals.update(kwargs)
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
                if self.quoter_map[t]:
                    seg = self.quoter_map[t](seg)
                ret += seg
            except Exception as e:
                if 'end_message' in str(t):
                    import pdb;pdb.post_mortem()
                ret += self.default_map[t]
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
