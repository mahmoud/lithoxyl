# -*- coding: utf-8 -*-

import inspect
import itertools

from strutils import indent


def wraps(func, injected=None, **kw):
    """Modeled after the built-in :func:`functools.wraps`, this version of
    `wraps` enables a decorator to be more informative and transparent
    than ever. Use `wraps` to make your wrapper functions have the
    same name, documentation, and signature information as the inner
    function that is being wrapped.

    By default, this version of `wraps` copies the inner function's
    signature exactly, allowing seamless introspection with the
    built-in :mod:`inspect` module. In addition, the outer signature
    can be modified. By passing a list of *injected* argument names,
    those arguments will be removed from the wrapper's signature.
    """
    # TODO: py3 for this and FunctionBuilder
    if injected is None:
        injected = []
    elif isinstance(injected, basestring):
        injected = [injected]

    update_dict = kw.pop('update_dict', True)
    if kw:
        raise TypeError('unexpected kwargs: %r' % kw.keys())

    fb = FunctionBuilder.from_func(func)
    for arg in injected:
        fb.remove_arg(arg)

    fb.body = 'return _call(%s)' % fb.get_sig_str()

    def wrapper_wrapper(wrapper_func):
        execdict = dict(_call=wrapper_func, _func=func)
        fully_wrapped = fb.get_func(execdict, with_dict=update_dict)

        return fully_wrapped

    return wrapper_wrapper


class FunctionBuilder(object):

    _defaults = {'args': [],
                 'varargs': None,
                 'keywords': None,
                 'defaults': (),
                 'doc': '',
                 'dict': {},
                 'module': None,
                 'body': 'pass',
                 'indent': 4}

    _compile_count = itertools.count()

    def __init__(self, name, **kw):
        self.name = name
        for a in self._defaults.keys():
            val = kw.pop(a, None)
            if val is None:
                val = self._defaults[a]
            setattr(self, a, val)

        if kw:
            raise TypeError('unexpected kwargs: %r' % kw.keys())
        return

    # def get_argspec(self):  # TODO

    def get_sig_str(self):
        return inspect.formatargspec(self.args, self.varargs,
                                     self.keywords, [])[1:-1]

    @classmethod
    def from_func(cls, func):
        # TODO: copy_body? gonna need a good signature regex.
        # TODO: might worry about __closure__?
        argspec = inspect.getargspec(func)
        kwargs = {'name': func.__name__,
                  'doc': func.__doc__,
                  'module': func.__module__,
                  'dict': getattr(func, '__dict__', {})}

        for a in ('args', 'varargs', 'keywords', 'defaults'):
            kwargs[a] = getattr(argspec, a)

        return cls(**kwargs)

    def get_func(self, execdict=None, add_source=True, with_dict=True):
        execdict = execdict or {}
        body = self.body or self._default_body

        tmpl = 'def {name}({sig_str}):'
        if self.doc:
            tmpl += '\n    """{doc}"""'
        tmpl += '\n{body}'

        body = indent(self.body, ' ' * self.indent)

        name = self.name.replace('<', '_').replace('>', '_')  # lambdas
        src = tmpl.format(name=name, sig_str=self.get_sig_str(),
                          doc=self.doc, body=body)

        self._compile(src, execdict)
        func = execdict[name]

        func.__name__ = self.name
        func.__doc__ = self.doc
        func.__defaults__ = self.defaults
        if with_dict:
            func.__dict__.update(self.dict)
        func.__module__ = self.module
        # TODO: caller module fallback?

        if add_source:
            func.__source__ = src

        return func

    def get_defaults_dict(self):
        ret = dict(reversed(zip(reversed(self.args),
                                reversed(self.defaults or []))))
        return ret

    def remove_arg(self, arg_name):
        d_dict = self.get_defaults_dict()
        try:
            self.args.remove(arg_name)
        except ValueError:
            raise ValueError('arg %r not found in %s argument list: %r'
                             % (arg_name, self.name, self.args))
        d_dict.pop(arg_name, None)
        self.defaults = tuple([d_dict[a] for a in self.args if a in d_dict])
        return

    def _compile(self, src, execdict):
        filename = ('<boltons.FunctionBuilder-%d>'
                    % (next(self._compile_count),))
        try:
            code = compile(src, filename, 'single')
            exec(code, execdict)
        except Exception:
            raise
        return execdict


"""decorator.py is bad because it excessively changes your decorator
API to be reliant on decorator.py's strange aesthetic. A pre-existing
decorator can't easily be migrated, and a decorator.py decorator is
not compatible with functools.wraps.

Function signature propagation is orthogonal to closure usage. The
author of decorator.py seems to find a problem with having a function
inside of a function and/or relying on closures and/or functools.wraps
interface.
"""
