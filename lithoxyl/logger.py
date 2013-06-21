# -*- coding: utf-8 -*-

import time

DEBUG = 20
INFO = 50
CRITICAL = 90


class Message(object):
    _is_trans = None
    _defer_publish = False

    def __init__(self, name, level=None, logger=None, **kwargs):
        self.name = name
        self.level = level
        self.status = kwargs.pop('status', None)
        self.message = kwargs.pop('message', None)
        self.data = kwargs.pop('data', {})  # TODO: payload?
        self.start_time = kwargs.pop('start_time', time.time())
        self.end_time = kwargs.pop('end_time', None)

        if kwargs:
            raise TypeError('unexpected keyword arguments: %r' % kwargs)

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

    def _complete(self, status, message):
        self.status = status
        self.message = message
        if not self._defer_publish:
            self.logger.enqueue(self)

    def __enter__(self):
        self._is_trans = self._defer_publish = True
        # TODO: reset start_time here?
        return self

    def __exit__(self, exc_type, exc_val, tb):
        self._defer_publish = False
        if exc_type:
            self.exception(exc_type, exc_val, tb)
        elif self.status is None:
            self.success(self.message)
        else:
            self._complete(self.status, self.message)


class Logger(object):
    def __init__(self, name, sinks, **kwargs):
        self.name = name
        self.sinks = sinks or []
        self.module = kwargs.pop('module', None)
        # TODO: get module

    def add_sink(self, sink):
        self.sinks.append(sink)

    def debug(self, name):
        return Message(name, level=DEBUG, logger=self)

    def info(self, name):
        return Message(name, level=INFO, logger=self)

    def critical(self, name):
        return Message(name, level=CRITICAL, logger=self)
