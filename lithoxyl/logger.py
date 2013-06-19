# -*- coding: utf-8 -*-

import time

DEBUG = 20
INFO = 50
CRITICAL = 90


class Message(object):
    def __init__(self, name, level=None, logger=None, **kwargs):
        self.name = name
        self.level = level
        self.status = kwargs.pop('status', None)
        self.data = kwargs.pop('data', {})  # TODO: payload?
        self.start_time = kwargs.pop('start_time', time.time())
        self.end_time = kwargs.pop('end_time', None)

        if kwargs:
            raise TypeError('unexpected keyword arguments: %r' % kwargs)

    def success(self, message):
        self._complete('success')

    def warning(self, message):
        self._complete('warning')

    def fail(self, message):  # TODO: failure?
        self._complete('fail')

    def exception(self, exc_obj, tb_obj):
        # TODO: format exc message
        # TODO: structure tb obj?
        self._complete('exception')

    def _complete(self, status, message):
        self.status = status
        self.logger.enqueue(self)


class Logger(object):
    def __init__(self, sinks, **kwargs):
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
