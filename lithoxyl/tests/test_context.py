import time
import signal

import pytest

from lithoxyl.logger import Logger
from lithoxyl.context import (
    get_context, set_context, LithoxylContext, note,
    signal_sysexit, install_sigterm_handler, uninstall_sigterm_handler,
    _consec_get_active_parent, _consec_set_active_parent,
)


def test_async_on_off():
    ctx = get_context()

    ctx.enable_async()
    time.sleep(0.25)  # 250ms should be plenty

    assert ctx.async_actor.is_alive()

    ctx.disable_async()
    time.sleep(0.1)  # 100ms should be plenty

    assert not ctx.async_actor.is_alive()

    return


def test_async_basic():
    ctx = get_context()

    ctx.enable_async()

    log = Logger('async_basic')
    with log.critical('test', reraise=False) as act:
        log.comment('i got a bad feeling about this')
        act.warn('here it comes')
        1 / 0
    log.flush()

    ctx.disable_async()
    return


def test_preflush_catching_and_noting():
    ctx = LithoxylContext()

    def raiser(log):
        raise RuntimeError('never gonna catch me')

    log = Logger('test_logger', context=ctx)
    log.preflush_hooks.append(raiser)

    notes = []

    def add_note(name, message):
        notes.append((name, message))

    ctx.note_handlers.append(add_note)

    ctx.enable_async()
    time.sleep(0.3)

    assert notes  # should have at least one note in 300ms



def test_add_remove_logger():
    ctx = LithoxylContext()
    log = Logger('add_remove_test', context=ctx)
    assert log in ctx.loggers
    ctx.remove_logger(log)
    assert log not in ctx.loggers
    # remove again should not raise
    ctx.remove_logger(log)


def test_context_flush():
    ctx = LithoxylContext()
    log = Logger('flush_test', context=ctx)
    # flush with no events should not raise
    ctx.flush()


def test_context_note_no_handlers():
    ctx = LithoxylContext()
    # no handlers, should return without error
    ctx.note('test', 'message %s', 'arg')


def test_context_note_with_handlers():
    ctx = LithoxylContext()
    notes = []
    ctx.note_handlers.append(lambda n, m: notes.append((n, m)))
    ctx.note('test', 'hello %s', 'world')
    assert notes == [('test', 'hello world')]


def test_context_note_format_error():
    ctx = LithoxylContext()
    notes = []
    ctx.note_handlers.append(lambda n, m: notes.append((n, m)))
    # Bad format string - should not raise, just pass through
    ctx.note('test', 'hello %d', 'not_a_number')
    assert len(notes) == 1


def test_set_get_context():
    old_ctx = get_context()
    new_ctx = LithoxylContext()
    ret = set_context(new_ctx)
    assert ret is new_ctx
    assert get_context() is new_ctx
    set_context(old_ctx)  # restore


def test_note_module_function():
    ctx = get_context()
    notes = []
    ctx.note_handlers.append(lambda n, m: notes.append((n, m)))
    note('test_note', 'hello')
    assert ('test_note', 'hello') in notes
    ctx.note_handlers.pop()


def test_consec_active_parent():
    ctx = LithoxylContext()
    log = Logger('parent_test', context=ctx)
    # No active parent initially
    assert _consec_get_active_parent(log, None) is None
    # Set active parent
    sentinel = object()
    _consec_set_active_parent(log, sentinel)
    assert _consec_get_active_parent(log, None) is sentinel
    # Unset (None)
    _consec_set_active_parent(log, None)
    assert _consec_get_active_parent(log, None) is None


def test_install_uninstall_sigterm_handler():
    # Save current handler
    original = signal.getsignal(signal.SIGTERM)
    try:
        # Reset to default first
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        assert install_sigterm_handler() is True
        assert signal.getsignal(signal.SIGTERM) is signal_sysexit
        # Installing again when already installed should be no-op
        assert install_sigterm_handler() is False
        # Uninstall
        assert uninstall_sigterm_handler() is True
        assert signal.getsignal(signal.SIGTERM) == signal.SIG_DFL
        # Uninstall again should be no-op
        assert uninstall_sigterm_handler() is False
    finally:
        signal.signal(signal.SIGTERM, original)


def test_signal_sysexit():
    with pytest.raises(SystemExit) as exc_info:
        signal_sysexit(15, None)
    assert exc_info.value.code == 143


def test_enable_async_bad_kwargs():
    ctx = LithoxylContext()
    with pytest.raises(TypeError, match='unexpected keyword'):
        ctx.enable_async(bogus=True)


def test_context_flush_exception():
    ctx = LithoxylContext()
    notes = []
    ctx.note_handlers.append(lambda n, m: notes.append((n, m)))

    class BadLogger:
        preflush_hooks = []
        def flush(self):
            raise RuntimeError('flush failed')
        def set_async(self, enabled):
            pass

    bad = BadLogger()  # keep reference for WeakKeyDictionary
    ctx.loggers[bad] = 999
    ctx.flush()  # should not raise
    assert any('context_flush' in n for n, m in notes)