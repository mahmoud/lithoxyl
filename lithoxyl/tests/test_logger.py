import pytest

from lithoxyl import Logger


def test_wrap():
    logger = Logger('t')

    @logger.wrap('critical')
    def t_func():
        return True

    assert t_func() is True

    @logger.wrap('critical', inject_as='yep')
    def y_func(yep):
        return bool(yep)

    assert y_func() is True

    # try inject_as with an argument that isn't there
    with pytest.raises(ValueError):
        @logger.wrap('critical', inject_as='nope')
        def t_func():
            return False

    return



def test_logger_flush():
    logger = Logger('t_flush')
    # flush with no events should work
    logger.flush()


def test_logger_preflush_hook_exception():
    notes = []
    from lithoxyl.context import LithoxylContext
    ctx = LithoxylContext()
    ctx.note_handlers.append(lambda n, m: notes.append((n, m)))
    logger = Logger('t_hook', context=ctx)

    def bad_hook(log):
        raise RuntimeError('hook failed')

    logger.preflush_hooks.append(bad_hook)
    logger.flush()  # should not raise
    assert any('preflush' in n for n, m in notes)


def test_logger_clear_sinks():
    logger = Logger('t_clear', sinks=[])
    from lithoxyl.sinks import AggregateSink
    agg = AggregateSink()
    logger.add_sink(agg)
    assert len(logger.sinks) == 1
    logger.clear_sinks()
    assert len(logger.sinks) == 0


def test_logger_repr_exception():
    logger = Logger('t_repr')
    r = repr(logger)
    assert 'Logger' in r