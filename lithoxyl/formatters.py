# -*- coding: utf-8 -*-

import json

from fields import BUILTIN_FIELD_MAP
from formatutils import tokenize_format_str

DEFAULT_QUOTER = json.dumps


class LazyExtrasDict(dict):
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
            raise TypeError('expected callable for Formatter.quoter, not %r'
                            % self.quoter)

        # NOTE: making this copy will be detrimental to a Formatter cache
        extra_field_map = dict([(f.fname, f) for f in extra_fields or []])
        self._field_map = dict(BUILTIN_FIELD_MAP, **extra_field_map)
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
            except:
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
class Formatter(object):
    def __init__(self, format_str, on_err=None):
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

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self._format_str)
"""

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
