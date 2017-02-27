# -*- coding: utf-8 -*-

import sys
import time
import itertools

from boltons.tbutils import ExceptionInfo, Callpoint
from boltons.cacheutils import cachedproperty

from lithoxyl.utils import int2hexguid_seq
from lithoxyl.common import to_unicode, get_level
from lithoxyl.context import note
from lithoxyl.sensible import SensibleMessageFormatter


_ACT_ID_ITER = itertools.count()


class DefaultException(Exception):
    "Only used when traceback extraction fails"


class Action(object):
    """The Action type is one of the core Lithoxyl types, and the key to
    instrumenting application logic. Actions are usually instantiated
    through convenience methods on :class:`~lithoxyl.logger.Logger`
    instances, associated with their level (e.g.,
    :meth:`~Logger.critical`).

    Args:
        logger: The Logger instance responsible for creating and
            publishing the Action.
        level: Log level of the Action. Generally one of
            :data:`~lithoxyl.common.DEBUG`,
            :data:`~lithoxyl.common.INFO`, or
            :data:`~lithoxyl.common.CRITICAL`. Defaults to ``None``.
        name (str): A string description of some application action.
        data (dict): A mapping of non-builtin fields to user
            values. Defaults to an empty dict (``{}``) and can be
            populated after Action creation by accessing the Action
            like a ``dict``.
        reraise (bool): Whether or not the Action should catch and
            reraise exceptions. Defaults to ``True``. Setting to
            ``False`` will cause all exceptions to be caught and
            logged appropriately, but not reraised. This should be
            used to eliminate ``try``/``except`` verbosity.
        frame: Frame of the callpoint creating the Action. Defaults to
            the caller's frame.

    Most of these parameters are managed by the Actions and respective
    :class:`~lithoxyl.Logger` themselves. While they are provided here
    for advanced use cases, usually only the *name* and *raw_message*
    are provided.

    Actions are :class:`dict`-like, and can be accessed as mappings

    and used to store additional structured data:

    >>> action['my_data'] = 20.0
    >>> action['my_lore'] = -action['my_data'] / 10.0
    >>> from pprint import pprint
    >>> pprint(action.data_map)
    {'my_data': 20.0, 'my_lore': -2.0}

    """
    _is_trans = None
    _defer_publish = False

    def __init__(self, logger, level, name,
                 data=None, reraise=True, parent=None, frame=None):
        self.action_id = next(_ACT_ID_ITER)
        self.logger = logger
        self.level = get_level(level)
        self.name = name

        self.data_map = data or {}
        self._reraise = reraise

        if frame is None:
            frame = sys._getframe(1)
        self.callpoint = Callpoint.from_frame(frame)

        self.begin_event = None
        self.end_event = None

        if parent:
            self.parent_action = parent
        else:
            self.parent_action = logger.context.get_active_parent(logger, self)
        return

    def __repr__(self):
        cn = self.__class__.__name__
        return ('<%s %r %s %r>'
                % (cn, self.name, self.level.name.upper(), self.status))

    @property
    def exc_event(self):
        return self.exc_events[-1] if self.exc_events else None

    @cachedproperty
    def exc_events(self):
        return []  # note that this is a cachedproperty

    @cachedproperty
    def warn_events(self):
        return []  # note that this is a cachedproperty

    @cachedproperty
    def guid(self):
        return int2hexguid_seq(self.action_id)

    @property
    def level_name(self):
        return self.level.name

    @property
    def status(self):
        try:
            return self.end_event.status
        except AttributeError:
            return 'begin'

    @property
    def duration(self):
        try:
            return self.end_event.etime - self.begin_event.etime
        except Exception:
            return 0.0

    @property  # TODO: cachedproperty? can this change?
    def parent_depth(self):
        i = 0
        while self.parent_action and i < 500:
            i += 1
            self = self.parent_action  # reuse var
        return i

    def begin(self, message=None, *a, **kw):
        self.data_map.update(kw)
        if not self.begin_event:
            if not message:
                message = self.name + ' beginning'

            self.begin_event = BeginEvent(self, time.time(), message, a)
            self.logger.on_begin(self.begin_event)
        return self

    def warn(self, message, *a, **kw):
        self.data_map.update(kw)
        warn_ev = WarningEvent(self, time.time(), message, a)
        self.warn_events.append(warn_ev)
        self.logger.on_warn(warn_ev)
        return self

    def success(self, message=None, *a, **kw):
        """Mark this Action successful. Also set the Action's
        *message* template. Positional and keyword arguments will be
        used to generate the formatted message. Keyword arguments will
        also be added to the Action's ``data_map`` attribute.
        """
        if not message:
            if self.data_map:
                message = self.name + ' succeeded - ({data_map_repr})'
            else:
                message = self.name + ' succeeded'
        return self._end('success', message, a, kw)

    def failure(self, message=None, *a, **kw):
        """Mark this Action failed. Also set the Action's
        *message* template. Positional and keyword arguments will be
        used to generate the formatted message. Keyword arguments will
        also be added to the Action's ``data_map`` attribute.
        """
        if not message:
            if self.data_map:
                message = self.name + ' failed - ({data_map_repr})'
            else:
                message = self.name + ' failed'

        return self._end('failure', message, a, kw)

    def exception(self, message=None, *a, **kw):
        """Mark this Action as having had an exception. Also
        sets the Action's *message* template similar to
        :meth:`Action.success` and :meth:`Action.failure`.

        Unlike those two attributes, this method is rarely called
        explicitly by application code, because the context manager
        aspect of the Action catches and sets the appropriate
        exception fields. When called explicitly, this method should
        only be called in an :keyword:`except` block.
        """
        exc_type, exc_val, exc_tb = sys.exc_info()
        return self._exception(exc_type, exc_val, exc_tb, message, a, kw)

    def _exception(self, exc_type, exc_val, exc_tb, message, fargs, data):
        exc_type = exc_type or DefaultException

        # have to capture the time now in case the on_exception sinks
        # take their sweet time
        etime = time.time()
        exc_info = ExceptionInfo.from_exc_info(exc_type, exc_val, exc_tb)
        if not message:
            cp = exc_info.tb_info.frames[-1]
            t = "%s raised exception: "
            exc_repr = "%s(%r)"
            errno = getattr(exc_val, 'errno', None)
            if errno and str(errno) not in exc_repr:
                t += exc_repr + ' (errno %s)' % exc_val.errno
            else:
                t += exc_repr
            t += " from %s on line %s of file '%s'"
            if self.data_map:
                t += ' - ({data_map_repr})'
            message = t % (self.name, exc_info.exc_type, exc_info.exc_msg,
                           cp.func_name, cp.lineno, cp.module_path)

        exc_event = ExceptionEvent(self, etime, message, fargs, exc_info)
        self.exc_events.append(exc_event)
        self.logger.on_exception(exc_event, exc_type, exc_val, exc_tb)

        return self._end('exception', message, fargs, data,
                         etime, exc_info)

    def _end(self, status, message, fargs, data, end_time=None, exc_info=None):
        self.data_map.update(data)

        if self._is_trans:
            end_time = end_time or time.time()
        else:
            if not self.begin_event:
                self.begin()
            end_time = self.begin_event.etime

        self.end_event = EndEvent(self, end_time, message,
                                  fargs, status, exc_info)

        if not self._defer_publish and self.logger:
            self.logger.on_end(self.end_event)

        return self

    def __enter__(self):
        self._is_trans = self._defer_publish = True
        self.logger.context.set_active_parent(self.logger, self)
        return self.begin()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._defer_publish = False
        if exc_type:
            try:
                self._exception(exc_type, exc_val, exc_tb,
                                message=None, fargs=(), data={})
            except Exception as e:
                note('action_exit',
                     'got %r while already handling exception %r', e, exc_val)
                pass  # TODO: still have to create end_event
        else:
            if self.end_event:
                self.logger.on_end(self.end_event)
            else:
                # now that _defer_publish=False, this will also publish
                self.success()

        self.logger.context.set_active_parent(self.logger, self.parent_action)

        if self._reraise is False:
            return True  # ignore exception
        return

    def __getitem__(self, key):
        return self.data_map[key]

    def __setitem__(self, key, value):
        self.data_map[key] = value

    def get_elapsed_time(self):
        """Simply get the amount of time that has passed since begin was
        called on this action, or 0.0 if it has not begun. This method
        has no side effects.
        """
        if self.begin_event:
            return time.time() - self.begin_event.etime
        return 0.0


# TODO: optimization strategy. if event creation starts to register on
# profiling, convert events to fixed-length tuples with empty
# dictionaries for caching lazy values. e.g.,
# ('begin', action, etime, event_id, to_unicode(raw_message), fargs, {})
#
# could also shove those as internal attrs on the action and put
# caching properties in place for the actual event objects. simplifies
# adding new fields.

class Event(object):
    _message = None

    def __getitem__(self, key):
        return self.action[key]

    def __getattr__(self, name):
        return getattr(self.action, name)

    @property
    def message(self):
        if self._message:
            return self._message

        raw_message = self.raw_message
        if raw_message is None:
            self._message = ''
        elif '{' not in raw_message:  # no templating, bypass
            self._message = raw_message
        else:
            # TODO: Formatter cache
            fmtr = SensibleMessageFormatter(raw_message, quoter=False)
            self._message = fmtr.format(self, *self.fargs)
        return self._message

    def __repr__(self):
        cn = self.__class__.__name__
        return '<%s %s %r>' % (cn, self.action_id, self.raw_message)


class BeginEvent(Event):
    status = 'begin'
    status_char = 'b'

    def __init__(self, action, etime, raw_message, fargs):
        self.action = action
        self.etime = etime
        self.event_id = next(_ACT_ID_ITER)
        self.raw_message = to_unicode(raw_message)
        self.fargs = fargs


class ExceptionEvent(Event):
    status = 'exception'
    status_char = '!'

    def __init__(self, action, etime, raw_message, fargs, exc_info):
        self.action = action
        self.etime = etime
        self.event_id = next(_ACT_ID_ITER)
        self.raw_message = to_unicode(raw_message)
        self.fargs = fargs
        self.exc_info = exc_info


class EndEvent(Event):
    def __init__(self, action, etime, raw_message, fargs, status,
                 exc_info=None):
        self.action = action
        self.etime = etime
        self.event_id = next(_ACT_ID_ITER)
        self.raw_message = to_unicode(raw_message)
        self.fargs = fargs
        self.status = status
        self.exc_info = exc_info

    @property
    def status_char(self):
        if self.action._is_trans:
            ret = self.status[:1].upper()
        else:
            ret = self.status[:1].lower()
        return ret


class WarningEvent(Event):
    status = 'warning'
    status_char = 'W'

    def __init__(self, action, etime, raw_message, fargs):
        self.action = action
        self.etime = etime
        self.event_id = next(_ACT_ID_ITER)
        self.raw_message = to_unicode(raw_message)
        self.fargs = fargs


class CommentEvent(Event):
    status = 'comment'
    status_char = '#'

    def __init__(self, action, etime, raw_message, fargs):
        self.action = action
        self.etime = etime
        self.event_id = next(_ACT_ID_ITER)
        self.raw_message = to_unicode(raw_message)
        self.fargs = fargs


"""What to do on multiple begins and multiple ends?

If a action is atomic (i.e., never entered/begun), then should it fire
a logger on_begin? Leaning no.

Should the BeginEvent be created on action creation? currently its
presence is used to track whether on_begin has been called on the
Logger yet.

Things that normally change on a Action currently:

 - Status
 - Message
 - Data map

Things which are populated:

 - end_time
 - duration

"""

"""naming rationale:

* 'warn', an action verb, was chosen over 'warning' because it implies
  repeatability, where as success/failure/exception are nouns, to
  indicate singular conclusion.

"""
