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
        self._complete_hooks = []
        self._begin_hooks = []
        for s in sinks:
            self.add_sink(s)

    def add_sink(self, sink):
        if sink in self._all_sinks:
            return
        self._all_sinks.append(sink)
        complete_hook = getattr(sink, 'on_complete', None)
        if callable(complete_hook):
            self._complete_hooks.append(complete_hook)
        begin_hook = getattr(sink, 'on_begin', None)
        if callable(begin_hook):
            self._begin_hooks.append(begin_hook)

    def on_complete(self, record):
        for complete_hook in self._complete_hooks:
            complete_hook(record)

    def on_begin(self, record):
        for begin_hook in self._begin_hooks:
            begin_hook(record)

    #def on_warn(self, record):
    #    pass

    #def on_exception(self, record, exc_obj, exc_type, exc_tb):
    #    pass

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
