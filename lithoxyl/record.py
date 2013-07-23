# -*- coding: utf-8 -*-

import sys
import time


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
        args = [getattr(self, s, None) for s in self.__slots__]
        if not any(args):
            return super(Callpoint, self).__repr__()
        else:
            return '%s(%s)' % (cn, ', '.join([repr(a) for a in args]))


class Record(object):
    _is_trans = None
    _defer_publish = False

    def __init__(self, name, level=None, **kwargs):
        self.name = name
        self.level = level
        self.logger = kwargs.pop('logger', None)
        self.status = kwargs.pop('status', None)
        self.message = kwargs.pop('message', None)
        self.extras = kwargs.pop('extras', {})
        self.start_time = kwargs.pop('start_time', time.time())
        self.end_time = kwargs.pop('end_time', None)
        self.warnings = []

        frame = kwargs.pop('frame', None)
        if frame is None:
            frame = sys._getframe(1)
        self.callpoint = Callpoint.from_frame(frame)

        if kwargs:
            self.extras.update(kwargs)

    def success(self, message):
        return self._complete('success', message)

    def warn(self, message):
        self.warnings.append(message)
        return self

    def failure(self, message):
        return self._complete('failure', message)

    def exception(self, exc_type, exc_val, tb_obj):
        # TODO: make real exc message
        # TODO: structure tb obj?
        return self._complete('exception', '%r, %r' % (exc_type, exc_val))

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
        return self

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
