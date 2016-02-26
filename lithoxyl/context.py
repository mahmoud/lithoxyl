# -*- coding: utf-8 -*-


LITHOXYL_CONTEXT = None


def get_context():
    global LITHOXYL_CONTEXT

    if not LITHOXYL_CONTEXT:
        LITHOXYL_CONTEXT = LithoxylContext()

    return LITHOXYL_CONTEXT


class LithoxylContext(object):
    def __init__(self):
        self.loggers = []
        self.async_actor = None

        # TODO: register atexit

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
