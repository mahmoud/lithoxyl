# -*- coding: utf-8 -*-

import time

DEBUG = 20
INFO = 50
CRITICAL = 90


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
        if not self._defer_publish and self.logger:
            # TODO: should logger be required?
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


class BaseLogger(object):
    def __init__(self, name, sinks, **kwargs):
        self.name = name
        self.sinks = sinks or []
        self.module = kwargs.pop('module', None)
        # TODO: get module

        if kwargs:
            raise TypeError('unexpected keyword arguments: %r' % kwargs)

    def add_sink(self, sink):
        # TODO: raise on sink not having a handle function
        self.sinks.append(sink)

    def enqueue(self, message):
        # TODO: need a convention for handling starts
        for sink in self.sinks:
            sink.handle(message)

    def debug(self, name):
        return Message(name, level=DEBUG, logger=self)

    def info(self, name):
        return Message(name, level=INFO, logger=self)

    def critical(self, name):
        return Message(name, level=CRITICAL, logger=self)


class AccumSink(object):
    def __init__(self):
        self.messages = []

    def handle(self, message):
        self.messages.append(message)


def main():
    acc = AccumSink()
    log = BaseLogger('test', [acc])
    test(log)
    test(log)
    import pdb;pdb.set_trace()


def test(logger):
    with logger.debug('hi') as t:
        t.success('yay')


if __name__ == '__main__':
    main()
