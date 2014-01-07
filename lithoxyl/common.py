# -*- coding: utf-8 -*-

from functools import total_ordering


@total_ordering
class Level(object):
    def __init__(self, name, value):
        self.name = name
        self._value = value

    def __eq__(self, other):
        if self is other:
            return True
        elif self._value == getattr(other, '_value', None):
            return True
        elif self._name == other:
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

MIN_LEVEL = Level('_min', 0)
MAX_LEVEL = Level('_max', 100)


if __name__ == '__main__':
    assert DEBUG != INFO != CRITICAL
    assert MIN_LEVEL < DEBUG < INFO < CRITICAL < MAX_LEVEL
    assert DEBUG <= INFO <= CRITICAL
    assert DEBUG == DEBUG
    assert DEBUG == Level('debug', 20)
