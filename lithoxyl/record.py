# -*- coding: utf-8 -*-

import sys
import time

from tbutils import TracebackInfo

_EXC_MSG = ('{exc_type_name}: {exc_msg} (line {exc_lineno} in file'
            ' {exc_filename}, logged from {callpoint_info})')


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
        self.raw_message = kwargs.pop('raw_message', None)
        self.extras = kwargs.pop('extras', {})
        self.begin_time = kwargs.pop('begin_time', time.time())
        self.end_time = kwargs.pop('end_time', None)
        self.duration = kwargs.pop('duration', 0.0)
        self._reraise = kwargs.pop('reraise', True)
        self.warnings = []

        self.exc_type = None
        self.exc_obj = None
        self.exc_tb_info = None

        frame = kwargs.pop('frame', None)
        if frame is None:
            frame = sys._getframe(1)
        self.callpoint = Callpoint.from_frame(frame)

        if kwargs:
            self.extras.update(kwargs)

    def success(self, message):
        # TODO: autogenerate success message
        return self._complete('success', message)

    def warn(self, message):
        self.warnings.append(message)
        return self

    def failure(self, message):
        return self._complete('failure', message)

    def exception(self, exc_type, exc_val, exc_tb):
        # TODO: make real exc message

        self.exc_type = exc_type
        self.exc_val = exc_val
        self.exc_tb_info = TracebackInfo.from_traceback(exc_tb)

        return self._complete('exception', '%r, %r' % (exc_type, exc_val))

    def __getitem__(self, key):
        try:
            return getattr(self, key)
        except AttributeError:
            return self.extras[key]

    def __setitem__(self, key, value):
        if hasattr(self, key):
            setattr(self, key, value)
        else:
            self.extras[key] = value

    def get_elapsed_time(self):
        return time.time() - self.begin_time

    @property
    def status_char(self):
        ret = '_'
        try:
            if self._is_trans:
                if self.end_time:
                    ret = self.status[:1].upper()
                else:
                    ret = 'b'
            else:
                ret = self.status[:1].lower()
        except:
            pass
        return ret

    def _complete(self, status, message):
        if self._is_trans:
            self.end_time = time.time()
            self.duration = self.end_time - self.begin_time

        self.status = status
        if not message:
            message = u''
        elif not isinstance(message, unicode):
            message = message.decode('utf-8')
        self.message = message
        if not self._defer_publish and self.logger:
            self.logger.on_complete(self)
        return self

    def __enter__(self):
        self._is_trans = self._defer_publish = True
        if self.logger:
            self.logger.on_begin(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._defer_publish = False
        if exc_type:
            try:
                # first, give any willing sinks a chance to handle exceptions
                self.logger.on_exception(self, exc_type, exc_val, exc_tb)
                # TODO: should there be a way for sinks to override
                # exception propagation here? probably not, I think.
            except:
                # TODO: something? grasshopper mode maybe.
                pass
            # then, normal completion behavior
            self.exception(exc_type, exc_val, exc_tb)
            # TODO: should probably be three steps:
            # set certain attributes, then do on_exception, then do completion.
        elif self.status is None:
            self.success(self.message)
        else:
            self._complete(self.status, self.message)
        if self._reraise is False:
            return True  # ignore exception
        return

    def __iter__(self):
        return iter([self, self])


def _main():
    with Record('test') as (r1, r2):
        print 1, r1
        print 2, r2


if __name__ == '__main__':
    _main()
