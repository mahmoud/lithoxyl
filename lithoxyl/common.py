# -*- coding: utf-8 -*-

from functools import total_ordering


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

MIN_LEVEL = Level('_min', 0)  # not to be registered
MAX_LEVEL = Level('_max', 100)


def _register_level(level_obj):
    global _SORTED_LEVELS
    LEVEL_ALIAS_MAP[level_obj.name.lower()] = level_obj
    LEVEL_ALIAS_MAP[level_obj.name.upper()] = level_obj
    LEVEL_ALIAS_MAP[level_obj._value] = level_obj
    LEVEL_ALIAS_MAP[level_obj] = level_obj
    _SORTED_LEVELS = sorted(set(LEVEL_ALIAS_MAP.values()))


_SORTED_LEVELS = None
LEVEL_ALIAS_MAP = {}
for level in BUILTIN_LEVELS:
    _register_level(level)
del level


def get_level(key):
    return LEVEL_ALIAS_MAP.get(key, DEFAULT_LEVEL)


def get_next_level(key, delta=1):
    level = get_level(key)
    next_i = min(_SORTED_LEVELS.index(level) + delta, len(_SORTED_LEVELS) - 1)
    next_level = _SORTED_LEVELS[next_i]
    return next_level


def get_prev_level(key, delta=1):
    level, delta = get_level(key), abs(delta)
    prev_i = max(_SORTED_LEVELS.index(level) - delta, 0)
    prev_level = _SORTED_LEVELS[prev_i]
    return prev_level


if __name__ == '__main__':
    assert DEBUG != INFO != CRITICAL
    assert MIN_LEVEL < DEBUG < INFO < CRITICAL < MAX_LEVEL
    assert DEBUG <= INFO <= CRITICAL
    assert DEBUG == DEBUG
    assert DEBUG == Level('debug', 20)
