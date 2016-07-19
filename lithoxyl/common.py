# -*- coding: utf-8 -*-

import time
from boltons.funcutils import total_ordering


EVENTS = ('begin', 'warn', 'end', 'exception', 'comment')
IMPORT_TIME = time.time()


def to_unicode(obj):
    try:
        return unicode(obj)
    except UnicodeDecodeError:
        return unicode(obj, encoding='utf8', errors='replace')


@total_ordering
class Level(object):
    def __init__(self, name, value):
        self.name = name.lower()
        self._value = value

    def __eq__(self, other):
        if self is other:
            return True
        elif self._value == getattr(other, '_value', None):
            return True
        elif self.name == other:
            return True
        return False

    def __lt__(self, other):
        if self is other:
            return False
        elif self._value < getattr(other, '_value', 100):
            return True
        return False

    def __repr__(self):
        return '%s(%r, %r)' % (self.__class__.__name__, self.name, self._value)


DEBUG = Level('debug', 20)
INFO = Level('info', 70)
CRITICAL = Level('critical', 90)
DEFAULT_LEVEL = DEBUG
BUILTIN_LEVELS = (DEBUG, INFO, CRITICAL)

MIN_LEVEL = Level('_min', 0)
MAX_LEVEL = Level('_max', 100)


def register_level(level_obj):
    if not isinstance(level_obj, Level):
        raise TypeError('expected Level object, not %r' % level_obj)

    LEVEL_ALIAS_MAP[level_obj.name.lower()] = level_obj
    LEVEL_ALIAS_MAP[level_obj.name.upper()] = level_obj
    LEVEL_ALIAS_MAP[level_obj._value] = level_obj
    LEVEL_ALIAS_MAP[level_obj] = level_obj
    LEVEL_LIST[:] = sorted(set(LEVEL_ALIAS_MAP.values()))


LEVEL_LIST = []
LEVEL_ALIAS_MAP = {}
register_level(MIN_LEVEL)
register_level(MAX_LEVEL)
for level in BUILTIN_LEVELS:
    register_level(level)
del level


def get_level(key, default=DEFAULT_LEVEL):
    return LEVEL_ALIAS_MAP.get(key, default)


def get_next_level(key, delta=1):
    level = get_level(key)
    next_i = min(LEVEL_LIST.index(level) + delta, len(LEVEL_LIST) - 1)
    next_level = LEVEL_LIST[next_i]
    return next_level


def get_prev_level(key, delta=1):
    level, delta = get_level(key), abs(delta)
    prev_i = max(LEVEL_LIST.index(level) - delta, 0)
    prev_level = LEVEL_LIST[prev_i]
    return prev_level
