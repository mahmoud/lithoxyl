import time
import threading
import pytest

from lithoxyl.actors import IntervalThreadActor, DEFAULT_INTERVAL


def test_construct_basic():
    actor = IntervalThreadActor(lambda: None, interval=50)
    assert not actor.is_alive()
    assert actor.interval == 50.0
    assert actor._orig_interval == 50.0
    assert actor.max_interval == 50.0 * 8
    assert actor._daemonize_thread is True
    assert actor._note is None


def test_construct_defaults():
    actor = IntervalThreadActor(lambda: None)
    assert actor.interval == float(DEFAULT_INTERVAL)


def test_construct_interval_none_uses_default():
    actor = IntervalThreadActor(lambda: None, interval=None)
    assert actor.interval == float(DEFAULT_INTERVAL)


def test_construct_non_callable_raises():
    with pytest.raises(ValueError, match='expected callable'):
        IntervalThreadActor('not_callable')


def test_construct_non_callable_note_raises():
    with pytest.raises(ValueError, match='expected callable for note'):
        IntervalThreadActor(lambda: None, note='bad')


def test_construct_unexpected_kwargs_raises():
    with pytest.raises(TypeError, match='unexpected keyword'):
        IntervalThreadActor(lambda: None, bogus=1)


def test_construct_max_interval():
    actor = IntervalThreadActor(lambda: None, interval=100, max_interval=500)
    assert actor.max_interval == 500.0


def test_start_stop_join():
    actor = IntervalThreadActor(lambda: None, interval=10)
    actor.start()
    time.sleep(0.05)
    assert actor.is_alive()
    actor.stop()
    actor.join(timeout=2.0)
    assert not actor.is_alive()


def test_get_stats():
    counter = {'n': 0}

    def task():
        counter['n'] += 1

    actor = IntervalThreadActor(task, interval=10)
    actor.start()
    time.sleep(0.1)
    actor.stop()
    actor.join(timeout=2.0)

    stats = actor.get_stats()
    assert 'run_start_time' in stats
    assert 'task_call_time' in stats
    assert 'task_call_count' in stats
    assert stats['run_start_time'] > 0
    assert stats['task_call_count'] >= 1
    assert stats['task_call_time'] >= 0


def test_task_exception_backoff():
    call_count = {'n': 0}
    fail_times = 3

    def flaky_task():
        call_count['n'] += 1
        if call_count['n'] <= fail_times:
            raise RuntimeError('boom')

    notes = []

    def note_cb(name, message):
        notes.append((name, message))

    actor = IntervalThreadActor(flaky_task, interval=10, note=note_cb)
    orig = actor._orig_interval
    actor.start()
    # Wait enough for failures + recovery
    time.sleep(0.5)
    actor.stop()
    actor.join(timeout=2.0)

    # Should have noted task exceptions
    assert len(notes) >= fail_times
    for name, msg in notes:
        assert name == 'actor_task_exception'
        assert 'raised' in msg

    # After recovery, interval should have decreased back toward original
    assert call_count['n'] > fail_times


def test_note_method():
    notes = []

    def note_cb(name, message):
        notes.append((name, message))

    actor = IntervalThreadActor(lambda: None, interval=10, note=note_cb)
    actor.note('test', 'hello')
    assert len(notes) == 1
    assert notes[0] == ('actor_test', 'hello')


def test_note_method_no_callback():
    actor = IntervalThreadActor(lambda: None, interval=10)
    # Should not raise
    actor.note('test', 'hello')


def test_join_before_start_raises():
    actor = IntervalThreadActor(lambda: None, interval=10)
    with pytest.raises(RuntimeError, match='must be started'):
        actor.join()


def test_double_start():
    actor = IntervalThreadActor(lambda: None, interval=10)
    actor.start()
    try:
        time.sleep(0.03)
        assert actor.is_alive()
        actor.start()  # should be no-op
        assert actor.is_alive()
    finally:
        actor.stop()
        actor.join(timeout=2.0)


def test_stop_when_not_alive():
    actor = IntervalThreadActor(lambda: None, interval=10)
    # Not started, stop should just clear stopping flag
    actor._stopping.set()
    actor.stop()
    assert not actor._stopping.is_set()


def test_daemonize_thread():
    actor = IntervalThreadActor(lambda: None, interval=10)
    actor.start()
    try:
        time.sleep(0.03)
        assert actor._thread.daemon is True
    finally:
        actor.stop()
        actor.join(timeout=2.0)


def test_daemonize_thread_false():
    actor = IntervalThreadActor(lambda: None, interval=10, daemonize_thread=False)
    actor.start()
    try:
        time.sleep(0.03)
        assert actor._thread.daemon is False
    finally:
        actor.stop()
        actor.join(timeout=2.0)


def test_join_returns_alive_status():
    actor = IntervalThreadActor(lambda: None, interval=10)
    actor.start()
    time.sleep(0.03)
    actor.stop()
    ret = actor.join(timeout=2.0)
    assert ret is False  # not alive after join


def test_interval_recovery_after_errors():
    """After errors increase interval, successful calls should bring it back down."""
    call_count = {'n': 0}

    def task():
        call_count['n'] += 1
        if call_count['n'] == 1:
            raise RuntimeError('first fail')

    actor = IntervalThreadActor(task, interval=10)
    actor.start()
    time.sleep(0.3)
    actor.stop()
    actor.join(timeout=2.0)

    # After recovery, interval should be back at or near original
    assert actor.interval <= actor._orig_interval * 2
