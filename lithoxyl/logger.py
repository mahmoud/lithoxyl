# -*- coding: utf-8 -*-

import sys

from record import Record

DEBUG = 20
INFO = 50
CRITICAL = 90


class BaseLogger(object):
    def __init__(self, name, sinks, **kwargs):
        # TODO: get module
        self.module = kwargs.pop('module', None)
        self.name = name or self.module
        self.sinks = sinks
        if kwargs:
            raise TypeError('unexpected keyword arguments: %r' % kwargs)

    @property
    def sinks(self):
        return self._all_sinks

    @sinks.setter
    def sinks(self, sinks):
        sinks = sinks or []
        self._all_sinks = []
        self._handlers = []
        self._begin_handlers = []
        for s in sinks:
            self.add_sink(s)

    def add_sink(self, sink):
        if sink in self._all_sinks:
            return
        self._all_sinks.append(sink)
        handle_f = getattr(sink, 'handle', None)
        if callable(handle_f):
            self._handlers.append(handle_f)
        handle_begin_f = getattr(sink, 'handle_begin', None)
        if callable(handle_begin_f):
            self._begin_handlers.append(handle_begin_f)

    def enqueue(self, record):
        for hfunc in self._handlers:
            hfunc(record)

    def enqueue_begin(self, record):
        for shfunc in self._begin_handlers:
            shfunc(record)

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
