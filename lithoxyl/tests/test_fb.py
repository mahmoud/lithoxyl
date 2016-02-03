
import inspect
from lithoxyl.utils import FunctionBuilder


def example_func(a, b, c=1, d=1):
    return (a + b) / d


def test_remove_arg():
    fb = FunctionBuilder.from_func(example_func)
    fb.body = '\n'.join(inspect.getsource(example_func).splitlines()[1:])

    new_func = fb.get_func()

    assert new_func(1, 2) == 3
    assert new_func(2, 4, d=2) == 3

    fb.remove_arg('c')
    no_c_func = fb.get_func()

    assert no_c_func(2, 4, 2) == 3


MISSING = object()


def obj_default_func(arg=MISSING):
    return arg


def test_hmm():
    fb = FunctionBuilder.from_func(obj_default_func)
    fb.body = '\n'.join(inspect.getsource(obj_default_func).splitlines()[1:])
    new_func = fb.get_func()

    assert new_func() is MISSING
