# -*- coding: utf-8 -*-

import time

class Message(object):
    def __init__(self, name, level=None, logger=None, **kwargs):
        self.name = name
        self.level = level
        self.status = kwargs.pop('status', None)
        self.data = kwargs.pop('data', {})  # TODO: payload?

    def success(self):
        pass

    def warn(self):
        pass

    def fail(self):
        pass

    def exception(self):
        pass

    def _complete(self, status):
        self.status = status
        self.logger.enqueue(self)


class Logger(object):
    def __init__(self, sinks):
        pass

    def add_sink(self, sink):
        pass

    def debug(self, name):
        pass

    def info(self, name):
        pass

    def critical(self, name):
        pass
