# -*- coding: utf-8 -*-
"""The :class:`Logger` is the application developer's primary
interface to using Lithoxyl. It is used to conveniently create
:class:`Records <Record>` and publish them to :class:`sinks <Sink>`.

"""

import sys

from record import Record
from common import DEBUG, INFO, CRITICAL, get_level


def _get_previous_frame(frame):
    try:
        return frame.f_back
    except AttributeError:
        raise ValueError('reached topmost frame in stack')


# TODO: should all sys._getframes be converted to use this?
# TODO: could precalculate offsets based on which methods are overridden
def get_frame_excluding_subtypes(target_type, offset=0):
    """
    `offset` is the number of additional frames to look up after
    reaching the outside of a class (in the event of a factory
    function or some such.
    """
    frame = sys._getframe(1)
    args = frame.f_code.co_varnames[:frame.f_code.co_argcount]
    first_arg_name = args[0] if args else ''
    i = 0
    while 1:
        i += 1
        first_arg = frame.f_locals.get(first_arg_name)
        if i > 10000:
            raise ValueError('could not get frame')
        if isinstance(first_arg, target_type):
            frame = _get_previous_frame(frame)
        elif isinstance(first_arg, type) and issubclass(first_arg, target_type):
            frame = _get_previous_frame(frame)
        else:
            break
    for i in xrange(offset):
        frame = _get_previous_frame(frame)
    return frame


class Logger(object):
    """The ``Logger`` is one of three core Lithoxyl types, and the main
    entrypoint to creating :class:`~lithoxyl.record.Record`
    instances. It is responsible for the fan-out of publishing
    :term:`records <record>` to :term:`sinks <sink>`.

    Args:
        name (str): Name of this Logger.
        sinks (list): A list of :term:`sink` objects to be attached to
            the Logger. Defaults to ``[]``. Sinks can be added later
            with :meth:`Logger.add_sink`.
        module (str): Name of the module where the new Logger instance
            will be stored.  Defaults to the module of the caller.

    The Logger is primarily used through its
    :class:`~lithoxyl.record.Record`-creating methods named after
    various log levels:

        * :meth:`Logger.critical`
        * :meth:`Logger.info`
        * :meth:`Logger.debug`

    Each creates a new :term:`record` with a given name, passing any
    additional keyword arguments on through to the
    :class:`lithoxyl.record.Record` constructor.
    """

    record_type = Record
    "Override *record_type* in subtypes for custom Record behavior."

    def __init__(self, name, sinks=None, **kwargs):
        self.module = kwargs.pop('module', None)
        self._module_offset = kwargs.pop('module_offset', 0)
        if self.module is None:
            frame = get_frame_excluding_subtypes(target_type=Logger,
                                                 offset=self._module_offset)
            self.module = frame.f_globals.get('__name__', '<module>')
        if kwargs:
            raise TypeError('unexpected keyword arguments: %r' % kwargs)
        self.name = name or self.module
        self.set_sinks(sinks)

    @property
    def sinks(self):
        """A copy of all sinks set on this Logger.
        Set sinks with :meth:`Logger.set_sinks`.
        """
        return list(self._all_sinks)

    def set_sinks(self, sinks):
        "Replace this Logger's sinks with *sinks*."
        sinks = sinks or []
        self._all_sinks = []
        self._begin_hooks = []
        self._warn_hooks = []
        self._complete_hooks = []
        self._exc_hooks = []
        for s in sinks:
            self.add_sink(s)

    def clear_sinks(self):
        "Clear this Logger's sinks."
        self.set_sinks([])

    def add_sink(self, sink):
        """Add *sink* to this Logger's sinks. Does nothing if *sink* is
        already in this Logger's sinks.
        """
        if sink in self._all_sinks:
            return
        begin_hook = getattr(sink, 'on_begin', None)
        if callable(begin_hook):
            self._begin_hooks.append(begin_hook)
        warn_hook = getattr(sink, 'on_warn', None)
        if callable(warn_hook):
            self._warn_hooks.append(warn_hook)
        complete_hook = getattr(sink, 'on_complete', None)
        if callable(complete_hook):
            self._complete_hooks.append(complete_hook)
        exc_hook = getattr(sink, 'on_exception', None)
        if callable(exc_hook):
            self._exc_hooks.append(exc_hook)
        self._all_sinks.append(sink)

    def on_complete(self, record):
        "Publish *record* to all sinks with ``on_complete()`` hooks."
        for complete_hook in self._complete_hooks:
            complete_hook(record)

    def on_begin(self, record):
        "Publish *record* to all sinks with ``on_begin()`` hooks."
        for begin_hook in self._begin_hooks:
            begin_hook(record)

    def on_warn(self, record):
        "Publish *record* to all sinks with ``on_warning()`` hooks."
        # TODO: need the actual warning as an argument?
        # TODO: warning module integration goes somewhere
        for warn_hook in self._warn_hooks:
            warn_hook(record)

    def on_exception(self, record, exc_type, exc_obj, exc_tb):
        "Publish *record* to all sinks with ``on_exception()`` hooks."
        for exc_hook in self._exc_hooks:
            exc_hook(record, exc_type, exc_obj, exc_tb)

    def debug(self, name, **kw):
        "Create and return a new :data:`DEBUG`-level :class:`Record` named *name*."
        kw['name'], kw['level'], kw['logger'] = name, DEBUG, self
        kw['frame'] = sys._getframe(1)
        return self.record_type(**kw)

    def info(self, name, **kw):
        "Create and return a new :data:`INFO`-level :class:`Record` named *name*."
        kw['name'], kw['level'], kw['logger'] = name, INFO, self
        kw['frame'] = sys._getframe(1)
        return self.record_type(**kw)

    def critical(self, name, **kw):
        "Create and return a new :data:`CRITICAL`-level :class:`Record` named *name*."
        kw['name'], kw['level'], kw['logger'] = name, CRITICAL, self
        kw['frame'] = sys._getframe(1)
        return self.record_type(**kw)

    def record(self, level, name, **kw):
        "Create and return a new :class:`Record` named *name* classified as *level*."
        kw['name'], kw['level'], kw['logger'] = name, get_level(level), self
        kw['frame'] = sys._getframe(1)
        return self.record_type(**kw)

    def wrap(self, level, name=None, inject_as=None, **kw):
        def record_wrapper(func_to_log, _name=name):
            if _name is None:  # wooo nonlocal
                _name = func_to_log.__name__
            @wraps(func_to_log, injected=inject_as)
            def logged_func(*a, **kw):
                rec = self.record(level, _name, **kw)
                if inject_as:
                    kw[inject_as] = rec
                with rec:
                    return func_to_log(*a, **kw)

            return logged_func

        return record_wrapper

    def __repr__(self):
        cn = self.__class__.__name__
        try:
            return '<%s name=%r sinks=%r>' % (cn, self.name, self.sinks)
        except:
            return object.__repr__(self)


def wraps(func, injected=None, **kw):
    # TODO: docstring
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


import inspect
import itertools

from strutils import iter_splitlines


def indent(text, margin, newline='\n', key=bool):
    indented_lines = [(margin + line if key(line) else line)
                      for line in iter_splitlines(text)]
    return newline.join(indented_lines)


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
                                     self.keywords, self.defaults)[1:-1]

    @classmethod
    def from_func(cls, func):
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
        d_dict.pop(arg_name)
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
