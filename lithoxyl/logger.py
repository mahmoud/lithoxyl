# -*- coding: utf-8 -*-
"""The :class:`Logger` is the application developer's primary
interface to using Lithoxyl. It is used to conveniently create
:class:`Actions <Action>` and publish them to :class:`sinks <Sink>`.

"""

import sys
import time
import itertools
from collections import deque
from threading import RLock

from boltons.funcutils import wraps

from lithoxyl.context import get_context
from lithoxyl.common import DEBUG, INFO, CRITICAL
from lithoxyl.action import Action, BeginEvent, EndEvent, CommentEvent


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
    entrypoint to creating :class:`~lithoxyl.action.Action` instances,
    and publishing those :term:`actions <action>` to :term:`sinks
    <sink>`.

    Args:
        name (str): Name of this Logger.
        sinks (list): A list of :term:`sink` objects to be attached to
            the Logger. Defaults to ``[]``. Sinks can be added later
            with :meth:`Logger.add_sink`.
        module (str): Name of the module where the new Logger instance
            will be stored.  Defaults to the module of the caller.

    Most Logger methods and attributes fal into three categories:
    :class:`~lithoxyl.action.Action` creation, Sink registration, and
    Event handling.
    """

    action_type = Action
    "Override *action_type* in subtypes for custom Action behavior."

    def __init__(self, name, sinks=None, **kwargs):
        self.logger_id = next(_LOG_ID_ITER)

        self.context = kwargs.pop('context', None) or get_context()
        self.context.add_logger(self)
        # TODO context-configurable
        self.event_queue = deque(maxlen=QUEUE_LIMIT)
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
        # ensures that actions are delivered to sinks in order
        with self.async_lock:
            for preflush_hook in self.preflush_hooks:
                try:
                    preflush_hook(self)
                except Exception as e:
                    self.context.note('preflush', 'hook %r got exception %r',
                                      preflush_hook, e)
            queue = self.event_queue
            while queue:
                ev_type, ev = queue.popleft()
                if ev_type == 'begin':
                    for begin_hook in self._begin_hooks:
                        begin_hook(ev)
                elif ev_type == 'end':
                    for end_hook in self._end_hooks:
                        end_hook(ev)
                elif ev_type == 'warn':
                    for warn_hook in self._warn_hooks:
                        warn_hook(ev)
                elif ev_type == 'comment':
                    for comment_hook in self._comment_hooks:
                        comment_hook(ev)
                else:
                    self.context.note('flush', 'unknown event type: %r %r',
                                      ev_type, ev)
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
        self._end_hooks = []
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
        end_hook = getattr(sink, 'on_end', None)
        if callable(end_hook):
            self._end_hooks.append(end_hook)
        exc_hook = getattr(sink, 'on_exception', None)
        if callable(exc_hook):
            self._exc_hooks.append(exc_hook)
        comment_hook = getattr(sink, 'on_comment', None)
        if callable(comment_hook):
            self._comment_hooks.append(comment_hook)
        # TODO: also pull flush methods?
        self._all_sinks.append(sink)

    def on_end(self, end_event):
        "Publish *end_event* to all sinks with ``on_end()`` hooks."
        if self.async_mode:
            self.event_queue.append(('end', end_event))
        else:
            for end_hook in self._end_hooks:
                end_hook(end_event)
        return

    def on_begin(self, begin_event):
        "Publish *begin_event* to all sinks with ``on_begin()`` hooks."
        if self.async_mode:
            self.event_queue.append(('begin', begin_event))
        else:
            for begin_hook in self._begin_hooks:
                begin_hook(begin_event)
        return

    def on_warn(self, warn_event):
        "Publish *warn_event* to all sinks with ``on_warn()`` hooks."
        if self.async_mode:
            self.event_queue.append(('warn', warn_event))
        else:
            for warn_hook in self._warn_hooks:
                warn_hook(warn_event)
        return

    def on_exception(self, exc_event, exc_type, exc_obj, exc_tb):
        "Publish *exc_event* to all sinks with ``on_exception()`` hooks."
        # async handling doesn't make sense here
        for exc_hook in self._exc_hooks:
            exc_hook(exc_event, exc_type, exc_obj, exc_tb)
        return

    def comment(self, message, *a, **kw):
        # Comment actions are not enterable, they're not
        # returned. They are always critical level, and always finish
        # with success. In fact, comment actions, as well as begin and
        # end events, along with their respective messages aren't to
        # be used directly, they're implemented for compatibility
        # reasons. They are not enqueued like other events. Only the
        # CommentEvent and its message are intended to be accessed
        # directly (e.g., through the event_message sensible formatter
        # field.

        act_type = self.action_type
        act = act_type(logger=self, level=CRITICAL, name='_comment',
                       data=kw, parent=kw.pop('parent_action', None))
        cur_time = time.time()

        act.begin_event = BeginEvent(act, cur_time,
                                     message + ' (begin comment)', a)
        act.end_event = EndEvent(act, cur_time,
                                 message + ' (end comment)', a, 'success')
        event = CommentEvent(act, cur_time, message, a)
        if self.async_mode:
            self.event_queue.append(('comment', event))
        else:
            for comment_hook in self._comment_hooks:
                comment_hook(event)
        return

    def debug(self, action_name, **kw):
        "Returns a new :data:`DEBUG`-level :class:`Action` named *name*."
        return self.action_type(logger=self, level=DEBUG, name=action_name,
                                data=kw, reraise=kw.pop('reraise', None),
                                parent=kw.pop('parent_action', None),
                                frame=sys._getframe(1))

    def info(self, action_name, **kw):
        "Returns a new :data:`INFO`-level :class:`Action` named *name*."
        return self.action_type(logger=self, level=INFO, name=action_name,
                                data=kw, reraise=kw.pop('reraise', None),
                                parent=kw.pop('parent_action', None),
                                frame=sys._getframe(1))

    def critical(self, action_name, **kw):
        "Returns a new :data:`CRITICAL`-level :class:`Action` named *name*."
        return self.action_type(logger=self, level=CRITICAL, name=action_name,
                                data=kw, reraise=kw.pop('reraise', None),
                                parent=kw.pop('parent_action', None),
                                frame=sys._getframe(1))

    def action(self, level, action_name, **kw):
        "Return a new :class:`Action` named *name* classified as *level*."
        return self.action_type(logger=self, level=level, name=action_name,
                                data=kw, reraise=kw.pop('reraise', None),
                                parent=kw.pop('parent_action', None),
                                frame=sys._getframe(1))

    def wrap(self, level, action_name=None,
             inject_as=None, enable_wrap=True, **kw):

        action_kwargs = kw

        def action_wrapper(func_to_log,
                           _enable=enable_wrap,
                           _name=action_name,
                           _action_kwargs=action_kwargs):
            if not _enable:
                return func_to_log
            if _name is None:  # wooo nonlocal
                _name = func_to_log.__name__

            @wraps(func_to_log, injected=inject_as)
            def logged_func(*a, **kw):
                act = self.action(level, _name, **action_kwargs)
                if inject_as:
                    kw[inject_as] = act
                with act:
                    return func_to_log(*a, **kw)

            wrapping_info = (self, level, action_name, func_to_log)
            logged_func.__lithoxyl_wrapped__ = wrapping_info

            return logged_func

        return action_wrapper

    def __repr__(self):
        cn = self.__class__.__name__
        try:
            return '<%s name=%r sinks=%r>' % (cn, self.name, self.sinks)
        except Exception:
            return object.__repr__(self)
