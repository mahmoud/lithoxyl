# -*- coding: utf-8 -*-

import time

from lithoxyl.logger import Logger
from lithoxyl.context import get_context, LithoxylContext


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
