
from lithoxyl.logger import FunctionBuilder


def example_func(a, b, c=0, d=1):
    return 'what a great example'


def test_remove_arg():
    fb = FunctionBuilder.from_func(example_func)

    fb.remove_arg('d')

    new_func = fb.get_func()
    src = new_func.__source__

    assert 'example_func(a, b, c=0):' in src

    fb = FunctionBuilder.from_func(example_func)

    fb.remove_arg('c')

    new_func = fb.get_func()
    src = new_func.__source__

    assert 'example_func(a, b, d=1):' in src
