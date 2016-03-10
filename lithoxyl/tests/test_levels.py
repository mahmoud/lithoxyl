
from lithoxyl.common import Level, DEBUG, INFO, CRITICAL
from lithoxyl.common import MIN_LEVEL, MAX_LEVEL, DEFAULT_LEVEL
from lithoxyl.common import get_level, get_next_level, get_prev_level


def test_default_level_ordering():
    assert DEBUG != INFO != CRITICAL
    assert MIN_LEVEL < DEBUG < INFO < CRITICAL < MAX_LEVEL
    assert DEBUG <= INFO <= CRITICAL
    assert DEBUG == DEBUG


def test_new_level_equality():
    assert DEBUG == Level('debug', 20)


def test_level_getting():
    assert get_level('debug') == DEBUG
    assert get_level('CRITICAL') == CRITICAL
    assert get_level(int(INFO._value)) == INFO
    assert get_level(DEFAULT_LEVEL) == DEFAULT_LEVEL


def test_level_adjacency():
    assert get_next_level(DEBUG) > DEBUG
    assert get_prev_level(CRITICAL) < CRITICAL
