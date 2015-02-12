# -*- coding: utf-8 -*-

import sys
import time

from tbutils import ExceptionInfo, Callpoint

from formatters import Formatter


class DefaultException(Exception):
    "Only used when traceback extraction fails"


class Record(object):
    _is_trans = None
    _defer_publish = False

    def __init__(self, name, level=None, **kwargs):
        self.name = name
        self.level = level
        self.logger = kwargs.pop('logger', None)
        self.status = kwargs.pop('status', 'begin')
        try:
            self.raw_message = kwargs.pop('raw_message')
        except:
            self.raw_message = '%s begin' % name
        self._message = kwargs.pop('message', None)
        self.extras = kwargs.pop('extras', {})
        self.begin_time = kwargs.pop('begin_time', time.time())
        self.end_time = kwargs.pop('end_time', None)
        self.duration = kwargs.pop('duration', 0.0)
        self._reraise = kwargs.pop('reraise', True)
        self.warnings = []

        self.exc_info = None

        frame = kwargs.pop('frame', None)
        if frame is None:
            frame = sys._getframe(1)
        self.callpoint = Callpoint.from_frame(frame)

        if kwargs:
            self.extras.update(kwargs)

    def __repr__(self):
        cn = self.__class__.__name__
        return '<%s %r %r>' % (cn, self.level, self.status)

    @property
    def level_name(self):
        try:
            return self.level.name
        except:
            return repr(self.level)

    def warn(self, message):
        self.warnings.append(message)
        return self

    def success(self, message=None, *a, **kw):
        if not message:
            message = self.name + ' succeeded'  # TODO: localize
        return self._complete('success', message, *a, **kw)

    def failure(self, message=None, *a, **kw):
        if not message:
            message = self.name + ' failed'
        return self._complete('failure', message, *a, **kw)

    def exception(self, message=None, *a, **kw):
        return self._exception(None, message, *a, **kw)

    def _exception(self, exc_info, message, *a, **kw):
        if not exc_info:
            exc_info = sys.exc_info()
        try:
            exc_type, exc_val, exc_tb = exc_info
        except:
            exc_type, exc_val, exc_tb = (None, None, None)
        exc_type = exc_type or DefaultException
        self.exc_info = ExceptionInfo.from_exc_info(exc_type, exc_val, exc_tb)
        if not message:
            message = '%s raised exception: %r' % (self.name, exc_val)
        return self._complete('exception', message, *a, **kw)

    def _complete(self, status, message=None, *a, **kw):
        self._pos_args = a
        self.extras.update(kw)
        if self._is_trans:
            self.end_time = time.time()
            self.duration = self.end_time - self.begin_time
        else:
            self.end_time, self.duration = self.begin_time, 0.0
        self.status = status
        if message is None:
            message = u''
        elif not isinstance(message, unicode):
            # if you think this is excessive, see the issue with the
            # unicode constructor as semi-detailed here:
            # http://pythondoeswhat.blogspot.com/2013/09/unicodebreakers.html
            try:
                message = str(message).decode('utf-8', errors='replace')
            except:
                message = unicode(object.__repr__(message))  # space nuke
        self.raw_message = message
        if not self._defer_publish and self.logger:
            self.logger.on_complete(self)
        return self

    @property
    def message(self):
        if self._message is not None:
            return self._message
        raw_message = self.raw_message
        if raw_message is None:
            return None

        if '{' not in raw_message:  # yay premature optimization
            self._message = raw_message
        else:
            # TODO: Formatter cache
            fmtr = Formatter(raw_message, quoter=False)
            self._message = fmtr.format_record(self, *self._pos_args)
        return self._message

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
            exc_info = (exc_type, exc_val, exc_tb)
            self._exception(exc_info, None)
            # TODO: should probably be three steps:
            # set certain attributes, then do on_exception, then do completion.
        elif self.status is 'begin':
            self.success()
        else:
            # TODO: a bit questionable
            self._complete(self.status, self.message)
        if self._reraise is False:
            return True  # ignore exception
        return

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

    @property
    def warn_char(self):
        return 'W' if self.warnings else ' '
