# -*- coding: utf-8 -*-
"""The :class:`Logger` is the application developer's primary
interface to using Lithoxyl. It is used to conveniently create
:class:`Records <Record>` and publish them to :class:`sinks <Sink>`.

"""

import sys
import time
import itertools
from collections import deque
from threading import RLock

from utils import wraps
from record import Record, BeginRecord, CompleteRecord, CommentRecord
from context import get_context
from common import DEBUG, INFO, CRITICAL


QUEUE_LIMIT = 10000
_LOG_ID_ITER = itertools.count()


def _get_previous_frame(frame):
    try:
        return frame.f_back
    except AttributeError:
        raise ValueError('reached topmost frame in stack')


# TODO: should all sys._getframes be converted to use this?
# TODO: could precalculate offsets based on which methods are overridden
# TODO: also precalculation could happen in a metaclass
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
        self.logger_id = next(_LOG_ID_ITER)

        self.context = kwargs.pop('context', None) or get_context()
        self.context.add_logger(self)
        # TODO context-configurable
        self.record_queue = deque(maxlen=QUEUE_LIMIT)
        self.async_mode = kwargs.pop('async', self.context.async_mode)
        self.async_lock = RLock()
        self.preflush_hooks = []
        self.last_flush = time.time()

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

    def set_async(self, enabled):
        self.async_mode = enabled

    def flush(self):
        # only one flush allowed to run at a time
        # ensures that records are delivered to sinks in order
        with self.async_lock:
            for preflush_hook in self.preflush_hooks:
                try:
                    preflush_hook(self)
                except Exception as e:
                    self.context.note('preflush', 'hook %r got exception %r',
                                      preflush_hook, e)
            queue = self.record_queue
            while queue:
                rec_type, rec = queue.popleft()
                if rec_type == 'begin':
                    for begin_hook in self._begin_hooks:
                        begin_hook(rec)
                elif rec_type == 'complete':
                    for complete_hook in self._complete_hooks:
                        complete_hook(rec)
                elif rec_type == 'warn':
                    for warn_hook in self._warn_hooks:
                        warn_hook(rec)
                elif rec_type == 'comment':
                    for comment_hook in self._comment_hooks:
                        comment_hook(rec)
                else:
                    self.context.note('flush', 'unknown event type: %r %r',
                                      rec_type, rec)
        self.last_flush = time.time()
        return

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
        self._comment_hooks = []
        for s in sinks:
            self.add_sink(s)

    def clear_sinks(self):
        "Clear this Logger's sinks."
        self.set_sinks([])

    def add_sink(self, sink):
        """Add *sink* to this Logger's sinks. Does nothing if *sink* is
        already in this Logger's sinks.
        """
        # TODO: check signatures?
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
        comment_hook = getattr(sink, 'on_comment', None)
        if callable(comment_hook):
            self._comment_hooks.append(comment_hook)
        # TODO: also pull flush methods?
        self._all_sinks.append(sink)

    def on_complete(self, complete_record):
        "Publish *record* to all sinks with ``on_complete()`` hooks."
        if self.async_mode:
            self.record_queue.append(('complete', complete_record))
        else:
            for complete_hook in self._complete_hooks:
                complete_hook(complete_record)
        return

    def on_begin(self, begin_record):
        "Publish *record* to all sinks with ``on_begin()`` hooks."
        if self.async_mode:
            self.record_queue.append(('begin', begin_record))
        else:
            for begin_hook in self._begin_hooks:
                begin_hook(begin_record)
        return

    def on_warn(self, warn_record):
        "Publish *record* to all sinks with ``on_warn()`` hooks."
        if self.async_mode:
            self.record_queue.append(('warn', warn_record))
        else:
            for warn_hook in self._warn_hooks:
                warn_hook(warn_record)
        return

    def on_exception(self, exc_record, exc_type, exc_obj, exc_tb):
        "Publish *record* to all sinks with ``on_exception()`` hooks."
        # async handling doesn't make sense here
        for exc_hook in self._exc_hooks:
            exc_hook(exc_record, exc_type, exc_obj, exc_tb)
        return

    def comment(self, message, *a, **kw):
        root_type = self.record_type
        root = root_type(logger=self, level=CRITICAL, name='comment', data=kw)
        cur_time = time.time()
        root.begin_record = BeginRecord(root, cur_time, 'comment', ())
        root.complete_record = CompleteRecord(root, cur_time,
                                              'comment', (), 'success')
        rec = CommentRecord(root, cur_time, message, a)
        if self.async_mode:
            self.record_queue.append(('comment', rec))
        else:
            for comment_hook in self._comment_hooks:
                comment_hook(rec)

    def debug(self, name, **kw):
        "Create and return a new :data:`DEBUG`-level :class:`Record` named *name*."
        return self.record_type(logger=self, level=DEBUG, name=name,
                                data=kw, reraise=kw.pop('reraise', None),
                                frame=sys._getframe(1))

    def info(self, name, **kw):
        "Create and return a new :data:`INFO`-level :class:`Record` named *name*."
        return self.record_type(logger=self, level=INFO, name=name,
                                data=kw, reraise=kw.pop('reraise', None),
                                frame=sys._getframe(1))

    def critical(self, name, **kw):
        "Create and return a new :data:`CRITICAL`-level :class:`Record` named *name*."
        return self.record_type(logger=self, level=CRITICAL, name=name,
                                data=kw, reraise=kw.pop('reraise', None),
                                frame=sys._getframe(1))

    def record(self, level, name, **kw):
        "Create and return a new :class:`Record` named *name* classified as *level*."
        return self.record_type(logger=self, level=level, name=name,
                                data=kw, reraise=kw.pop('reraise', None),
                                frame=sys._getframe(1))

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
        except Exception:
            return object.__repr__(self)
