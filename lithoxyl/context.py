# -*- coding: utf-8 -*-

import atexit

from actors import IntervalThreadActor

DEFAULT_JOIN_TIMEOUT = 0.5

LITHOXYL_CONTEXT = None


def get_context():
    if not LITHOXYL_CONTEXT:
        set_context(LithoxylContext())

    return LITHOXYL_CONTEXT


def set_context(context):
    global LITHOXYL_CONTEXT

    LITHOXYL_CONTEXT = context

    return context


class LithoxylContext(object):
    def __init__(self, **kwargs):
        self.loggers = []

        self.async_mode = False
        self.async_actor = None
        self.async_timeout = DEFAULT_JOIN_TIMEOUT

        atexit.register(self._stop_async)

    def _stop_async(self, timeout=None):
        print 'stop_async start'
        if timeout is None:
            timeout = self.async_timeout
        if self.async_actor:
            self.async_actor.stop()
            self.async_actor.join(timeout)
        self.flush()
        print 'stop_async done'

    def set_async(self, enabled, **kwargs):
        update_actor = kwargs.pop('update_actor', True)
        join_timeout = kwargs.pop('join_timeout', None)
        update_loggers = kwargs.pop('update_loggers', True)

        actor_kw = {'interval': kwargs.pop('interval', None),
                    'max_interval': kwargs.pop('max_interval', None),
                    'daemonize_thread': kwargs.pop('daemonize_thread', True)}
        if kwargs:
            raise TypeError('unexpected keyword arguments: %r' % kwargs.keys())

        self.async_mode = enabled

        if enabled:
            if update_actor:
                if not self.async_actor:
                    self.async_actor = IntervalThreadActor(task=self.flush,
                                                           **actor_kw)
                self.async_actor.start()
        else:
            if update_actor and self.async_actor:
                self.async_actor.stop()
                self.async_actor.join(join_timeout)
                self.flush()

        if update_loggers:
            for logger in self.loggers:
                logger.set_async(enabled)

        return

    def flush(self):
        for logger in self.loggers:
            logger.flush()
        return

    def add_logger(self, logger):
        if logger not in self.loggers:
            self.loggers.append(logger)

    def remove_logger(self, logger):
        try:
            self.loggers.remove(logger)
        except ValueError:
            pass


"""Actors must:

 1. have a re-entrant .stop() function that gracefully shuts down the
   actor if it is running

"""
