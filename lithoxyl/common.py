# -*- coding: utf-8 -*-

from functools import total_ordering


@total_ordering
class Level(str):
    def __new__(cls, name, *a, **kw):
        return str.__new__(Level, name)

    def __init__(self, name, value):
        self.name = name
        self._value = value

    def __eq__(self, other):
        if self is other or self.name == getattr(other, 'name', other):
            return True
        return False

    def __gt__(self, other):
        if self is other:
            return False
        elif self._value > getattr(other, '_value', 100):
            # default to high so that logging errors might be noticed sooner
            return True
        return False

    def __repr__(self):
        return '%s(%r, %r)' % (self.__class__.__name__, self.name, self._value)


DEBUG = Level('debug', 20)
INFO = Level('info', 70)
CRITICAL = Level('critical', 90)
