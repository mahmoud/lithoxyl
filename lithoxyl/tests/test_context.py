# -*- coding: utf-8 -*-

import time

from lithoxyl.context import get_context


def test_async_on_off():
    ctx = get_context()

    ctx.enable_async()
    time.sleep(0.25)  # 250ms should be plenty

    assert ctx.async_actor.is_alive()

    ctx.disable_async()
    time.sleep(0.1)  # 100ms should be plenty

    assert not ctx.async_actor.is_alive()

    return
