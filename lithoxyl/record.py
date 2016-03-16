# -*- coding: utf-8 -*-

import sys
import time
import itertools

from boltons.tbutils import ExceptionInfo, Callpoint

from lithoxyl.context import note
from lithoxyl.formatters import SensibleFormatter
from lithoxyl.common import to_unicode, get_level


_REC_ID_ITER = itertools.count()


class DefaultException(Exception):
    "Only used when traceback extraction fails"


class Record(object):
    """The ``Record`` type is one of the three core Lithoxyl types, and
    the underlying currency of the Lithoxyl system. Records are
    usually instantiated through convenience methods on
    :class:`~lithoxyl.logger.Logger` instances, and most
    instrumentation will be done through populating records with
    relevant data.

    Args:
        logger: The Logger instance responsible for creating (and
            publishing) the Record.
        level: Log level of the Record. Generally one of
            :data:`~lithoxyl.common.DEBUG`,
            :data:`~lithoxyl.common.INFO`, or
            :data:`~lithoxyl.common.CRITICAL`. Defaults to ``None``.
        name (str): The Record name describes some application action.
        data (dict): A mapping of non-builtin fields to user
            values. Defaults to an empty dict (``{}``) and can be
            populated after Record creation by accessing the Record
            like a ``dict``.
        reraise (bool): Whether or not the Record should catch and
            reraise exceptions. Defaults to ``True``. Setting to
            ``False`` will cause all exceptions to be caught and
            logged appropriately, but not reraised. This should be
            used to eliminate ``try``/``except`` verbosity.
        frame: Frame of the callpoint creating the Record. Defaults to
            the caller's frame.

    All additional keyword arguments are automatically included in the
    Record's ``data_map`` attribute.

    >>> record = Record('our_mission', CRITICAL, mission='explore new worlds')

    Most of these parameters are managed by the Records and respective
    Loggers themselves. While they are provided here for advanced use
    cases, usually only the *name*, *raw_message*, *reraise*, and
    extra values should be provided.

    Records are :class:`dict`-like, and can be accessed as mappings

    and used to store additional structured data:

    >>> record['my_data'] = 20.0
    >>> record['my_lore'] = -record['my_data'] / 10.0
    >>> from pprint import pprint
    >>> pprint(record.data_map)
    {'mission': 'explore new worlds', 'my_data': 20.0, 'my_lore': -2.0}

    """
    _is_trans = None
    _defer_publish = False

    def __init__(self, logger, level, name,
                 data=None, reraise=True, frame=None):
        self.record_id = next(_REC_ID_ITER)
        self.logger = logger
        self.level = get_level(level)
        self.name = name

        self.data_map = data or {}
        self._reraise = reraise

        if frame is None:
            frame = sys._getframe(1)
        self.callpoint = Callpoint.from_frame(frame)

        self.begin_event = None
        self.complete_event = None
        # these can go internal and be lazily created through properties
        self.warn_events = []
        self.exc_events = []

        self.parent_record = logger.context.get_active_parent(logger, self)
        return

    def __repr__(self):
        cn = self.__class__.__name__
        return ('<%s %r %s %r>'
                % (cn, self.name, self.level.name.upper(), self.status))

    @property
    def level_name(self):
        return self.level.name

    @property
    def status(self):
        try:
            return self.complete_event.status
        except AttributeError:
            return 'begin'

    @property
    def duration(self):
        try:
            return self.complete_event.ctime - self.begin_event.ctime
        except Exception:
            return 0.0

    def begin(self, message=None, *a, **kw):
        self.data_map.update(kw)
        if not self.begin_event:
            if not message:
                message = self.name + ' begun'

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
        """Mark this Record as complete and successful. Also set the Record's
        *message* template. Positional and keyword arguments will be
        used to generate the formatted message. Keyword arguments will
        also be added to the Record's ``data_map`` attribute.
        """
        if not message:
            message = self.name + ' succeeded'
        return self._complete('success', message, a, kw)

    def failure(self, message=None, *a, **kw):
        """Mark this Record as complete and failed. Also set the Record's
        *message* template. Positional and keyword arguments will be
        used to generate the formatted message. Keyword arguments will
        also be added to the Record's ``data_map`` attribute.
        """
        if not message:
            message = self.name + ' failed'
        return self._complete('failure', message, a, kw)

    def exception(self, message=None, *a, **kw):
        """Mark this Record as complete and having had an exception. Also
        sets the Record's *message* template similar to
        :meth:`Record.success` and :meth:`Record.failure`.

        Unlike those two attributes, this method is rarely called
        explicitly by application code, because the context manager
        aspect of the Record catches and sets the appropriate
        exception fields. When called explicitly, this method should
        only be called in an :keyword:`except` block.
        """
        exc_type, exc_val, exc_tb = sys.exc_info()
        return self._exception(exc_type, exc_val, exc_tb, message, a, kw)

    def _exception(self, exc_type, exc_val, exc_tb, message, fargs, data):
        exc_type = exc_type or DefaultException

        # have to capture the time now in case the on_exception sinks
        # take their sweet time
        ctime = time.time()
        exc_info = ExceptionInfo.from_exc_info(exc_type, exc_val, exc_tb)
        if not message:
            message = '%s raised exception: %r' % (self.name, exc_val)

        self.exc_event = ExceptionEvent(self, ctime, message, fargs, exc_info)
        self.logger.on_exception(self.exc_event, exc_type, exc_val, exc_tb)

        return self._complete('exception', message, fargs, data,
                              ctime, exc_info)

    def _complete(self, status, message, fargs, data,
                  end_time=None, exc_info=None):
        self.data_map.update(data)

        if self._is_trans:
            end_time = end_time or time.time()
        else:
            if not self.begin_event:
                self.begin()
            end_time = self.begin_event.ctime

        self.complete_event = CompleteEvent(self, end_time, message,
                                            fargs, status, exc_info)

        if not self._defer_publish and self.logger:
            self.logger.on_complete(self.complete_event)

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
                note('record_exit',
                     'got %r while already handling exception %r', e, exc_val)
                pass  # TODO: still have to create complete_event
        else:
            if self.complete_event:
                self.logger.on_complete(self.complete_event)
            else:
                # now that _defer_publish=False, this will also publish
                self.success()

        self.logger.context.set_active_parent(self.logger, self.parent_record)

        if self._reraise is False:
            return True  # ignore exception
        return

    def __getitem__(self, key):
        try:
            return getattr(self, key)
        except AttributeError:
            return self.data_map[key]

    def __setitem__(self, key, value):
        if hasattr(self, key):
            setattr(self, key, value)
        else:
            self.data_map[key] = value

    def get_elapsed_time(self):
        """Simply get the amount of time that has passed since the record was
        created or begun. This method has no side effects.
        """
        if self.begin_event:
            return time.time() - self.begin_event.ctime
        return 0.0

    '''
    @property
    def status_char(self):
        """A single-character representation of the status of the Record. See
        the ``status_chr`` field in the
        :class:`~lithoxyl.formatter.Formatter` field documentation for
        more details.
        """
        ret = '_'
        try:
            if self._is_trans:
                if self.end_time:
                    ret = self.status[:1].upper()
                else:
                    ret = 'b'
            else:
                ret = self.status[:1].lower()
        except Exception:
            pass
        return ret

    @property
    def warn_char(self):
        "``'W'`` if the Record has warnings, ``' '`` otherwise."
        return 'W' if self.warnings else ' '
    '''


# TODO: optimization strategy. if event creation starts to register on
# profiling, convert events to fixed-length tuples with empty
# dictionaries for caching lazy values. e.g.,
# ('begin', record, ctime, event_id, to_unicode(raw_message), fargs, {})
#
# could also shove those as internal attrs on the record and put
# caching properties in place for the actual event objects. simplifies
# adding new fields.

class Event(object):
    _message = None

    def __getitem__(self, key):
        return self.record[key]

    def __getattr__(self, name):
        return getattr(self.record, name)

    @property
    def message(self):
        if self._message:
            return self._message

        raw_message = self.raw_message
        if raw_message is None:
            self._message = ''
        elif '{' not in raw_message:  # yay premature optimization
            self._message = raw_message
        else:
            # TODO: Formatter cache
            fmtr = SensibleFormatter(raw_message, quoter=False)
            self._message = fmtr.format(self, *self.fargs)
        return self._message

    def __repr__(self):
        cn = self.__class__.__name__
        return '<%s %s %r>' % (cn, self.record_id, self.raw_message)


class BeginEvent(Event):
    status_char = 'b'

    def __init__(self, record, ctime, raw_message, fargs):
        self.record = record
        self.ctime = ctime
        self.event_id = next(_REC_ID_ITER)
        self.raw_message = to_unicode(raw_message)
        self.fargs = fargs


class ExceptionEvent(Event):
    status_char = '!'

    def __init__(self, record, ctime, raw_message, fargs, exc_info):
        self.record = record
        self.ctime = ctime
        self.event_id = next(_REC_ID_ITER)
        self.raw_message = to_unicode(raw_message)
        self.fargs = fargs
        self.exc_info = exc_info


class CompleteEvent(Event):
    def __init__(self, record, ctime, raw_message, fargs, status,
                 exc_info=None):
        self.record = record
        self.ctime = ctime
        self.event_id = next(_REC_ID_ITER)
        self.raw_message = to_unicode(raw_message)
        self.fargs = fargs
        self.status = status
        self.exc_info = exc_info

    @property
    def status_char(self):
        if self.record._is_trans:
            ret = self.status[:1].upper()
        else:
            ret = self.status[:1].lower()
        return ret


class WarningEvent(Event):
    status_char = 'W'

    def __init__(self, record, ctime, raw_message, fargs):
        self.record = record
        self.ctime = ctime
        self.event_id = next(_REC_ID_ITER)
        self.raw_message = to_unicode(raw_message)
        self.fargs = fargs


class CommentEvent(Event):
    status_char = '#'

    def __init__(self, record, ctime, raw_message, fargs):
        self.record = record
        self.ctime = ctime
        self.event_id = next(_REC_ID_ITER)
        self.raw_message = to_unicode(raw_message)
        self.fargs = fargs


"""What to do on multiple begins and multiple completes?

If a record is atomic (i.e., never entered/begun), then should it fire
a logger on_begin? Leaning no.

Should the BeginEvent be created on record creation? currently its
presence is used to track whether on_begin has been called on the
Logger yet.

Things that normally change on a Record currently:

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
