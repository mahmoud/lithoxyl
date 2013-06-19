# -*- coding: utf-8 -*-


class Message(object):
    def __init__(self, name, logger=None):
        self.name = name
        self.status = None
        self.data = {}

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
