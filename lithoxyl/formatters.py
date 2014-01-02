# -*- coding: utf-8 -*-

from json import dumps as escape_str

from formatutils import tokenize_format_str
from fields import FMT_BUILTIN_MAP, BUILTIN_GETTERS, BUILTIN_QUOTERS


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
        for token in self.tokens:
            try:
                if not token.fspec:
                    token.set_fspec(FMT_BUILTIN_MAP[token.fname].fspec)
                self.default_map[token] = self.defaulter(token)
                self.quote_map[token] = self.quoter(token)
            except (KeyError, AttributeError):
                # not a field or not a builtin field
                pass
        return

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
        return BUILTIN_QUOTERS.get(token.fname)

    __call__ = format_record


class Formatter(object):
    # TODO: inherit from templette?

    def __init__(self, format_str):
        self._format_str = format_str
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

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self._format_str)


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
