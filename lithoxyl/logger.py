# -*- coding: utf-8 -*-

import sys
import time

DEBUG = 20
INFO = 50
CRITICAL = 90


class Callpoint(object):
    __slots__ = ('func_name', 'lineno', 'module_name', 'module_path', 'lasti')

    def __init__(self, module_name, module_path, func_name, lineno, lasti):
        self.func_name = func_name
        self.lineno = lineno
        self.module_name = module_name
        self.module_path = module_path
        self.lasti = lasti

    @classmethod
    def from_frame(cls, frame):
        func_name = frame.f_code.co_name
        lineno = frame.f_lineno
        module_name = frame.f_globals.get('__name__', '')
        module_path = frame.f_code.co_filename
        lasti = frame.f_lasti
        return cls(module_name, module_path, func_name, lineno, lasti)

    def __repr__(self):
        cn = self.__class__.__name__
        args = [repr(getattr(self, s, None)) for s in self.__slots__]
        if not any(args):
            return super(Callpoint, self).__repr__()
        else:
            return '%s(%s)' % (cn, ', '.join(args))


class Message(object):
    _is_trans = None
    _defer_publish = False

    def __init__(self, name, level=None, **kwargs):
        self.name = name
        self.level = level
        self.logger = kwargs.pop('logger', None)
        self.status = kwargs.pop('status', None)
        self.message = kwargs.pop('message', None)
        self.data = kwargs.pop('data', {})  # TODO: payload?
        self.start_time = kwargs.pop('start_time', time.time())
        self.end_time = kwargs.pop('end_time', None)

        frame = kwargs.pop('frame', None)
        if frame is None:
            frame = sys._getframe(1)
        self.callpoint = Callpoint.from_frame(frame)

        if kwargs:
            self.data.update(kwargs)

    def success(self, message):
        self._complete('success', message)

    def warning(self, message):
        self._complete('warning', message)

    def fail(self, message):  # TODO: failure?
        self._complete('fail', message)

    def exception(self, exc_type, exc_val, tb_obj):
        # TODO: make real exc message
        # TODO: structure tb obj?
        self._complete('exception', '%r, %r' % (exc_type, exc_val))

    @property
    def duration(self):
        if self.end_time:
            return self.end_time - self.start_time
        elif self._is_trans:
            return time.time() - self.start_time
        else:
            return 0.0

    def _complete(self, status, message):
        self.status = status
        self.message = message
        if self._is_trans:
            self.end_time = time.time()
        if not self._defer_publish and self.logger:
            # TODO: should logger be required?
            self.logger.enqueue(self)

    def __enter__(self):
        self._is_trans = self._defer_publish = True

        self.logger.enqueue_start(self)
        return self

    def __exit__(self, exc_type, exc_val, tb):
        self._defer_publish = False
        if exc_type:
            self.exception(exc_type, exc_val, tb)
        elif self.status is None:
            self.success(self.message)
        else:
            self._complete(self.status, self.message)


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
        self._start_handlers = []
        for s in sinks:
            self.add_sink(s)

    def add_sink(self, sink):
        if sink in self._all_sinks:
            return
        self._all_sinks.append(sink)
        handle_f = getattr(sink, 'handle', None)
        if callable(handle_f):
            self._handlers.append(handle_f)
        handle_start_f = getattr(sink, 'handle_start', None)
        if callable(handle_start_f):
            self._start_handlers.append(handle_start_f)

    def enqueue(self, message):
        for hfunc in self._handlers:
            hfunc(message)

    def enqueue_start(self, message):
        for shfunc in self._start_handlers:
            shfunc(message)

    def debug(self, name, **kw):
        kw['name'], kw['level'], kw['logger'] = name, DEBUG, self
        kw['frame'] = sys._getframe(1)
        return Message(**kw)

    def info(self, name, **kw):
        kw['name'], kw['level'], kw['logger'] = name, INFO, self
        kw['frame'] = sys._getframe(1)
        return Message(**kw)

    def critical(self, name, **kw):
        kw['name'], kw['level'], kw['logger'] = name, CRITICAL, self
        kw['frame'] = sys._getframe(1)
        return Message(**kw)
