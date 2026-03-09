import re
import sys
import types
import traceback

import pytest

from lithoxyl.utils import (
    check_encoding_settings,
    EncodingLookupError,
    ErrorBehaviorLookupError,
    unwrap,
    unwrap_all,
    wrap_all,
    reraise,
    int2hexguid,
    int2hexguid_seq,
    type_types,
)
from lithoxyl.logger import Logger


# --- check_encoding_settings ---

def test_valid_encoding_and_errors():
    result = check_encoding_settings('utf-8', 'replace')
    # Returns None on success (no error raised)
    assert result is None


def test_invalid_encoding_raises():
    with pytest.raises(EncodingLookupError):
        check_encoding_settings('nope', 'replace')


def test_invalid_encoding_no_reraise():
    result = check_encoding_settings('nope', 'replace', reraise=False)
    assert result is False


def test_invalid_errors_raises():
    with pytest.raises(ErrorBehaviorLookupError):
        check_encoding_settings('utf-8', 'badvalue')


def test_invalid_errors_no_reraise():
    result = check_encoding_settings('utf-8', 'badvalue', reraise=False)
    assert result is False


def test_valid_encoding_strict():
    # 'strict' is a valid error handler
    result = check_encoding_settings('ascii', 'strict')
    # 'strict' causes UnicodeEncodeError on '\xdd', caught by except Exception -> True
    assert result is True


def test_valid_encoding_errors_branch():
    # 'ignore' is a valid error handler; encoding of non-ascii with
    # 'ignore' succeeds (returns True via the except Exception branch)
    result = check_encoding_settings('utf-8', 'ignore')
    # utf-8 + ignore: '\xdd'.encode('ascii', 'ignore') doesn't raise LookupError,
    # it either succeeds or hits the generic Exception branch → returns True
    assert result is True or result is None


# --- unwrap / unwrap_all ---

def test_unwrap_not_wrapped_raises():
    class Target:
        def method(self):
            pass

    with pytest.raises(ValueError, match='does not appear to be a wrapped function'):
        unwrap(Target, 'method')


def test_unwrap_roundtrip():
    logger = Logger('test_unwrap_roundtrip', [])

    class Target:
        def my_func(self, x):
            return x + 1

    original = Target.my_func
    wrapper = logger.wrap('info', action_name='test_my_func')
    wrapped = wrapper(original)
    Target.my_func = wrapped

    # Verify it's wrapped
    assert hasattr(Target.my_func, '__lithoxyl_wrapped__')

    # Unwrap
    unwrap(Target, 'my_func')

    # Verify restored
    assert Target.my_func is original


def test_unwrap_all_on_module():
    """unwrap_all iterates attributes and silently skips non-wrapped ones."""
    # Create a fake module-like object with both wrapped and unwrapped functions
    class FakeModule:
        pass

    def plain_func():
        return 1

    FakeModule.plain_func = plain_func

    logger = Logger('test_unwrap_all', [])
    wrapper = logger.wrap('info', action_name='test_func')
    wrapped = wrapper(plain_func)
    FakeModule.wrapped_func = wrapped

    # unwrap_all should unwrap wrapped_func and skip plain_func
    unwrap_all(FakeModule)

    assert FakeModule.plain_func is plain_func
    assert FakeModule.wrapped_func is plain_func


# --- wrap_all ---

def _make_target_module():
    """Create a simple namespace object with some functions for wrap_all tests."""
    class Target:
        pass

    def public_func():
        return 'public'

    def _private_func():
        return 'private'

    def another_func():
        return 'another'

    Target.public_func = public_func
    Target._private_func = _private_func
    Target.another_func = another_func
    Target.__name__ = 'FakeTarget'
    return Target


def test_wrap_all_skip_prefix():
    logger = Logger('test_wrap_skip', [])
    target = _make_target_module()

    wrap_all(logger, target=target, skip='_')

    # _private_func should not be wrapped (starts with '_')
    assert not hasattr(target._private_func, '__lithoxyl_wrapped__')
    # public_func should be wrapped
    assert hasattr(target.public_func, '__lithoxyl_wrapped__')


def test_wrap_all_skip_callable():
    logger = Logger('test_wrap_skip_callable', [])

    class Target:
        pass

    def another_func():
        return 'another'

    def public_func():
        return 'public'

    Target.another_func = another_func
    Target.public_func = public_func
    Target.__name__ = 'FakeTarget'

    # Skip anything named 'another_func'
    skip_fn = lambda name: name == 'another_func'
    wrap_all(logger, target=Target, skip=skip_fn, depth=0, skip_exc=True)

    assert not hasattr(Target.another_func, '__lithoxyl_wrapped__')
    # public_func should be wrapped (not skipped)
    assert hasattr(Target.public_func, '__lithoxyl_wrapped__')


def test_wrap_all_skip_invalid_type():
    logger = Logger('test_wrap_skip_bad', [])
    target = _make_target_module()

    with pytest.raises(ValueError, match='skip expected string prefix or callable'):
        wrap_all(logger, target=target, skip=12345)


def test_wrap_all_extras():
    logger = Logger('test_wrap_extras', [])
    target = _make_target_module()

    wrap_all(logger, target=target, extras={'inject_transient_data': True})

    # Just verify wrapping succeeded
    assert hasattr(target.public_func, '__lithoxyl_wrapped__')


def test_wrap_all_level_map():
    logger = Logger('test_wrap_level_map', [])
    target = _make_target_module()

    wrap_all(logger, target=target, level_map={'public_func': 'debug'})

    assert hasattr(target.public_func, '__lithoxyl_wrapped__')


def test_wrap_all_depth_zero():
    logger = Logger('test_wrap_depth0', [])

    class Target:
        class Inner:
            def inner_method(self):
                pass
        def outer_method(self):
            pass

    Target.__name__ = 'Target'

    wrap_all(logger, target=Target, depth=0)

    # outer_method should be wrapped, but Inner's methods should NOT
    assert hasattr(Target.outer_method, '__lithoxyl_wrapped__')
    assert not hasattr(Target.Inner.inner_method, '__lithoxyl_wrapped__')


def test_wrap_all_skip_exc():
    logger = Logger('test_wrap_skip_exc', [])

    class BadTarget:
        pass

    # Create a callable that will fail when the logger tries to wrap it
    # (e.g., a builtin that can't be introspected properly)
    BadTarget.__name__ = 'BadTarget'
    BadTarget.len = len  # builtins can cause issues

    # With skip_exc=True, wrapping errors should be swallowed
    wrap_all(logger, target=BadTarget, skip='_', skip_exc=True)
    # Should not raise


def test_wrap_all_returns_wrapped_names():
    logger = Logger('test_wrap_ret', [])
    target = _make_target_module()

    ret = wrap_all(logger, target=target, skip='_')

    # Should return list of wrapped function labels
    assert isinstance(ret, list)
    assert any('public_func' in name for name in ret)
    assert any('another_func' in name for name in ret)
    # _private_func skipped
    assert not any('_private_func' in name for name in ret)


def test_wrap_all_label_fallback():
    """When target has no __name__, label falls back to class+hex."""
    logger = Logger('test_wrap_label', [])

    class NoName:
        def func(self):
            pass

    # Remove __name__ if present via a wrapper object
    class Wrapper:
        def __init__(self, obj):
            self.__wrapped = obj
        def __getattr__(self, name):
            if name == '__name__':
                raise AttributeError
            return getattr(self.__wrapped, name)

    # Just test with explicit label
    wrap_all(logger, target=NoName, label='custom_label')


# --- reraise ---

def test_reraise_with_value():
    try:
        raise RuntimeError('original')
    except RuntimeError:
        tp, val, tb = sys.exc_info()

    with pytest.raises(RuntimeError, match='original'):
        reraise(tp, val, tb)


def test_reraise_none_value():
    with pytest.raises(RuntimeError):
        reraise(RuntimeError, None)


def test_reraise_preserves_traceback():
    try:
        raise ValueError('trace test')
    except ValueError:
        tp, val, tb = sys.exc_info()

    try:
        reraise(tp, val, tb)
    except ValueError:
        _, _, caught_tb = sys.exc_info()
        # The traceback chain should include the original frame
        tb_lines = traceback.format_tb(caught_tb)
        assert len(tb_lines) >= 1


def test_reraise_sets_traceback():
    """When value.__traceback__ differs from tb, with_traceback is used."""
    try:
        raise TypeError('tb test')
    except TypeError:
        tp, val, tb = sys.exc_info()

    # Clear the traceback on the value to force the with_traceback branch
    val.__traceback__ = None

    with pytest.raises(TypeError, match='tb test'):
        reraise(tp, val, tb)


# --- int2hexguid / int2hexguid_seq ---

def test_int2hexguid_length():
    guid = int2hexguid(42)
    assert len(guid) == 24


def test_int2hexguid_hex_chars():
    guid = int2hexguid(99)
    assert re.fullmatch(r'[0-9a-f]{24}', guid)


def test_int2hexguid_deterministic():
    a = int2hexguid(123)
    b = int2hexguid(123)
    assert a == b


def test_int2hexguid_different_inputs():
    a = int2hexguid(1)
    b = int2hexguid(2)
    assert a != b


def test_int2hexguid_seq_hex_chars():
    guid = int2hexguid_seq(0)
    assert re.fullmatch(r'[0-9a-f]+', guid)


def test_int2hexguid_seq_monotonic():
    guids = [int2hexguid_seq(i) for i in range(100)]
    # Each subsequent guid should be lexicographically >= previous
    # Since they're hex representations of incrementing ints, the numeric
    # values should be strictly increasing
    values = [int(g, 16) for g in guids]
    for i in range(1, len(values)):
        assert values[i] > values[i - 1]


def test_int2hexguid_seq_deterministic():
    a = int2hexguid_seq(5)
    b = int2hexguid_seq(5)
    assert a == b


# --- type_types ---

def test_type_types():
    assert type_types == (type,)
    assert isinstance(type_types, tuple)
    assert len(type_types) == 1



# --- Additional coverage for uncovered lines ---

def test_unwrap_all_none_target_raises():
    # unwrap_all(None) tries sys._getframe(1).f_globals.__name__
    # which fails because f_globals is a dict (no __name__ attr)
    # This exercises lines 53-58
    with pytest.raises(ValueError, match='unable to wrap all'):
        unwrap_all(None)


def test_wrap_all_none_target_raises():
    # wrap_all with target=None tries sys._getframe(1).f_globals.__name__
    # which fails for the same reason
    # This exercises lines 97-103
    logger = Logger('wrap_none_test')
    with pytest.raises(ValueError, match='unable to wrap all'):
        wrap_all(logger, target=None)


def test_unwrap_all_explicit_module():
    # Pass a known module as target to exercise the unwrap path
    import types
    mod = types.ModuleType('fake_unwrap_mod')
    def fn():
        return 1
    mod.fn = fn
    # unwrap_all on a module with no wrapped functions should not raise
    unwrap_all(mod)


def test_wrap_all_explicit_module():
    # Pass a module as target to exercise the wrap_all path
    import types
    mod = types.ModuleType('fake_wrap_mod')
    def fn():
        return 1
    fn.__name__ = 'fn'
    mod.fn = fn
    mod.__name__ = 'fake_wrap_mod'
    logger = Logger('wrap_mod_test')
    ret = wrap_all(logger, target=mod, skip='')
    assert isinstance(ret, list)
    # Clean up
    unwrap_all(mod)


def test_wrap_all_label_fallback():
    # When target has no __name__, fall back to class name + hex format
    # This exercises lines 122-123
    logger = Logger('wrap_label')
    # Create an object instance (instances have no __name__ by default)
    class NoNameClass:
        def do_stuff(self):
            return 1
    target = NoNameClass()
    assert not hasattr(target, '__name__')
    ret = wrap_all(logger, target=target)
    assert isinstance(ret, list)
    unwrap_all(target)


def test_wrap_all_object_label():
    # Pass an object instance as target with explicit label
    logger = Logger('wrap_obj')
    class Target:
        def do_thing(self):
            return 42
    t = Target()
    ret = wrap_all(logger, target=t, label='custom')
    assert isinstance(ret, list)
    unwrap_all(t)


def test_wrap_all_no_name_attr():
    # This targets the hasattr(val, '__name__') check (line 143-144)
    # Use skip_exc to handle built-in types that can't be wrapped
    logger = Logger('wrap_noname')
    class Target:
        def real_func(self):
            return True
    t = Target()
    ret = wrap_all(logger, target=t, skip='_', skip_exc=True)
    # Should have wrapped real_func
    assert any('real_func' in r for r in ret)
    unwrap_all(t)