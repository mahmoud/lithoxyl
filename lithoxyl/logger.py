# -*- coding: utf-8 -*-

import sys

from record import Record
from common import DEBUG, INFO, CRITICAL


class BaseLogger(object):
    def __init__(self, name, sinks=None, **kwargs):
        # TODO: get module
        self.module = kwargs.pop('module', None)
        if kwargs:
            raise TypeError('unexpected keyword arguments: %r' % kwargs)
        self.name = name or self.module
        self.set_sinks(sinks)

    @property
    def sinks(self):
        return list(self._all_sinks)

    def set_sinks(self, sinks):
        sinks = sinks or []
        self._all_sinks = []
        self._begin_hooks = []
        self._warn_hooks = []
        self._complete_hooks = []
        self._exc_hooks = []
        for s in sinks:
            self.add_sink(s)

    def clear_sinks(self):
        self.set_sinks(None)

    def add_sink(self, sink):
        if sink in self._all_sinks:
            return
        begin_hook = getattr(sink, 'on_begin', None)
        if callable(begin_hook):
            self._begin_hooks.append(begin_hook)
        warn_hook = getattr(sink, 'on_warn', None)
        if callable(warn_hook):
            self._warn_hooks.append(warn_hook)
        complete_hook = getattr(sink, 'on_complete', None)
        if callable(complete_hook):
            self._complete_hooks.append(complete_hook)
        exc_hook = getattr(sink, 'on_exception', None)
        if callable(exc_hook):
            self._exc_hooks.append(exc_hook)
        self._all_sinks.append(sink)

    def on_complete(self, record):
        for complete_hook in self._complete_hooks:
            complete_hook(record)

    def on_begin(self, record):
        for begin_hook in self._begin_hooks:
            begin_hook(record)

    def on_warn(self, record):
        # TODO: need the actual warning as an argument?
        # TODO: warning module integration goes somewhere
        for warn_hook in self._warn_hooks:
            warn_hook(record)

    def on_exception(self, record, exc_type, exc_obj, exc_tb):
        for exc_hook in self._exc_hooks:
            exc_hook(record, exc_type, exc_obj, exc_tb)

    def debug(self, name, **kw):
        kw['name'], kw['level'], kw['logger'] = name, DEBUG, self
        kw['frame'] = sys._getframe(1)
        return Record(**kw)

    def info(self, name, **kw):
        kw['name'], kw['level'], kw['logger'] = name, INFO, self
        kw['frame'] = sys._getframe(1)
        return Record(**kw)

    def critical(self, name, **kw):
        kw['name'], kw['level'], kw['logger'] = name, CRITICAL, self
        kw['frame'] = sys._getframe(1)
        return Record(**kw)

    def record(self, name, level, **kw):
        kw['name'], kw['level'], kw['logger'] = name, level, self
        kw['frame'] = sys._getframe(1)
        return Record(**kw)

    def __repr__(self):
        cn = self.__class__.__name__
        return '<%s name=%r sinks=%r>' % (cn, self.name, self.sinks)
