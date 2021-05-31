
from __future__ import absolute_import
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
