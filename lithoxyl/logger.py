# -*- coding: utf-8 -*-

import sys

from record import Record
from common import DEBUG, INFO, CRITICAL


def _get_previous_frame(frame):
    try:
        return frame.f_back
    except AttributeError:
        raise ValueError('reached topmost frame in stack')


# TODO: should all sys._getframes be converted to use this?
def get_frame_excluding_subtypes(target_type, offset=0):
    """
    `offset` is the number of additional frames to look up after
    reaching the outside of a class (in the event of a factory
    function or some such.
    """
    frame = sys._getframe(1)
    args = frame.f_code.co_varnames[:frame.f_code.co_argcount]
    first_arg_name = args[0] if args else ''
    i = 0
    while 1:
        i += 1
        first_arg = frame.f_locals.get(first_arg_name)
        if i > 10000:
            raise ValueError('could not get frame')
        if isinstance(first_arg, target_type):
            frame = _get_previous_frame(frame)
        elif isinstance(first_arg, type) and issubclass(first_arg, target_type):
            frame = _get_previous_frame(frame)
        else:
            break
    for i in xrange(offset):
        frame = _get_previous_frame(frame)
    return frame


class Logger(object):
    record_type = Record

    def __init__(self, name, sinks=None, **kwargs):
        self.module = kwargs.pop('module', None)
        self._module_offset = kwargs.pop('module_offset', 0)
        if self.module is None:
            frame = get_frame_excluding_subtypes(target_type=Logger,
                                                 offset=self._module_offset)
            self.module = frame.f_globals.get('__name__', '<module>')
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
        return self.record_type(**kw)

    def info(self, name, **kw):
        kw['name'], kw['level'], kw['logger'] = name, INFO, self
        kw['frame'] = sys._getframe(1)
        return self.record_type(**kw)

    def critical(self, name, **kw):
        kw['name'], kw['level'], kw['logger'] = name, CRITICAL, self
        kw['frame'] = sys._getframe(1)
        return self.record_type(**kw)

    def record(self, name, level, **kw):
        kw['name'], kw['level'], kw['logger'] = name, level, self
        kw['frame'] = sys._getframe(1)
        return self.record_type(**kw)

    def __repr__(self):
        cn = self.__class__.__name__
        try:
            return '<%s name=%r sinks=%r>' % (cn, self.name, self.sinks)
        except:
            return object.__repr__(self)
