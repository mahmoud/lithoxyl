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

    assert repr(DEBUG) == "Level('debug', 20)"


def test_level_adjacency():
    assert get_next_level(DEBUG) > DEBUG
    assert get_prev_level(CRITICAL) < CRITICAL



def test_register_level_type_error():
    from lithoxyl.common import register_level
    import pytest
    with pytest.raises(TypeError, match='expected Level object'):
        register_level('not-a-level')


def test_level_hash():
    assert hash(DEBUG) == hash(Level('debug', 20))
    assert hash(DEBUG) != hash(INFO)


def test_level_eq_by_value():
    new_level = Level('debug', 20)
    assert DEBUG == new_level


def test_level_eq_by_name():
    assert DEBUG == 'debug'
    assert DEBUG != 'info'


def test_level_lt_fallback():
    # When comparing with non-Level without _value, uses default 100
    assert DEBUG < 'zzz'  # getattr(other, '_value', 100) = 100, DEBUG._value=20 < 100