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

        # graceful thread shutdown and sink flushing
        atexit.register(self.disable_async)

    def enable_async(self, **kwargs):
        update_loggers = kwargs.pop('update_loggers', True)
        update_actor = kwargs.pop('update_actor', True)
        actor_kw = {'interval': kwargs.pop('interval', None),
                    'max_interval': kwargs.pop('max_interval', None),
                    # be very careful when not daemonizing thread
                    'daemonize_thread': kwargs.pop('daemonize_thread', True)}
        if kwargs:
            raise TypeError('unexpected keyword arguments: %r' % kwargs.keys())

        self.async_mode = True

        if update_actor:
            if not self.async_actor:
                self.async_actor = IntervalThreadActor(self.flush, **actor_kw)
            self.async_actor.start()

        if update_loggers:
            for logger in self.loggers:
                logger.set_async(False)
        return

    def disable_async(self, **kwargs):
        update_loggers = kwargs.pop('update_loggers', True)
        update_actor = kwargs.pop('update_actor', True)
        join_timeout = kwargs.pop('join_timeout', self.async_timeout)

        if update_actor and self.async_actor:
            self.async_actor.stop()
            self.async_actor.join(join_timeout)

        if update_loggers:
            for logger in self.loggers:
                logger.set_async(False)

        self.flush()
        self.async_mode = False

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
