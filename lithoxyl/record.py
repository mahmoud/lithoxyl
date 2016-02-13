# -*- coding: utf-8 -*-

import sys
import time

from tbutils import ExceptionInfo, Callpoint

from common import DEBUG, INFO, CRITICAL, to_unicode
from formatters import Formatter


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
        name (str): The name of the Record.
        level: Log level of the Record. Generally one of
            :data:`~lithoxyl.common.DEBUG`,
            :data:`~lithoxyl.common.INFO`, or
            :data:`~lithoxyl.common.CRITICAL`. Defaults to ``None``.
        logger: The Logger instance responsible for creating (and
            publishing) the Record.
        status (str): State of the task represented by the Record. One
            of 'begin', 'success', 'failure', or 'exception'. Defaults
            to 'begin'.
        extras (dict): A mapping of non-builtin fields to user
            values. Defaults to ``{}`` and can be populated after
            Record creation by accessing the Record like a ``dict``.
        raw_message (str): A message or message template that further
            describes the status of the record.
            Defaults to ``'<name> <status>'``, using the values above.
        message (str): A pre-formatted message that similar to
            *raw_message*, but will not be treated as a template.
        begin_time (float): A timestamp of when the Record was created
            or started. Defaults to the output of :func:`time.time`.
        end_time (float): A timestamp of when the Record was
            completed, assuming it is a transactional record. Defaults
            to ``None``, which is valid when a record is incomplete or
            is not transactional and thus has no duration.
        duration (float): The duration of the record. Defaults to ``0.0``.
        frame: Frame of the callpoint creating the Record. Defaults to
            the caller's frame.
        reraise (bool): Whether or not the Record should catch and
            reraise exceptions. Defaults to ``True``. Setting to
            ``False`` will cause all exceptions to be caught and
            logged appropriately, but not reraised. This should be
            used to eliminate ``try``/``except`` verbosity.

    All additional keyword arguments are automatically included in the
    Record's ``extras`` attribute.

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
    >>> pprint(record.extras)
    {'mission': 'explore new worlds', 'my_data': 20.0, 'my_lore': -2.0}
    """
    _is_trans = None
    _defer_publish = False

    # itertools.count?

    def __init__(self, logger, level, name, **kwargs):
        self.logger = logger
        self.level = level
        self.name = name

        self.data_map = kwargs.pop('data', {})
        self._reraise = kwargs.pop('reraise', True)

        frame = kwargs.pop('frame', None)
        if frame is None:
            frame = sys._getframe(1)
        self.callpoint = Callpoint.from_frame(frame)
        if kwargs:
            self.data_map.update(kwargs)

        self.begin_record = None  # TODO: may have to make BeginRecord here
        self.complete_record = None
        self.warn_records = []
        self.exc_records = []
        return

    def __repr__(self):
        cn = self.__class__.__name__
        # TODO on the upper() stuff. better repr for level?
        return ('<%s %r %s %r>'
                % (cn, self.name, self.level.name.upper(), self.status))

    @property
    def level_name(self):
        try:
            return self.level.name
        except Exception:
            return repr(self.level)

    def begin(self, message=None, *a, **kw):
        self.data_map.update(kw)
        self.begin_record = BeginRecord(self, time.time(), message, a)
        self.logger.on_begin(self.begin_record)
        return self

    def warn(self, message, *a, **kw):
        self.data_map.update(kw)
        warn_rec = WarnRecord(self, time.time(), message, a)
        self.warn_records.append(warn_rec)
        self.logger.on_complete(warn_rec)
        return self

    def success(self, message=None, *a, **kw):
        """Mark this Record as complete and successful. Also set the Record's
        *message* template. Positional and keyword arguments will be
        used to generate the formatted message. Keyword arguments will
        also be added to the Record's ``extras`` attribute.

        >>> record = Record('important_task', CRITICAL)
        >>> record.success('{record_name} {status_str}: {0} {my_kwarg}', 'this is', my_kwarg='fun')
        <Record CRITICAL 'success'>
        >>> record.message
        u'important_task success: this is fun'
        """
        if not message:
            message = self.name + ' succeeded'
        return self._complete('success', message, a, kw)

    def failure(self, message=None, *a, **kw):
        """Mark this Record as complete and failed. Also set the Record's
        *message* template. Positional and keyword arguments will be
        used to generate the formatted message. Keyword arguments will
        also be added to the Record's ``extras`` attribute.

        >>> record = Record('important_task', CRITICAL)
        >>> record.failure('{record_name} {status_str}: {0} {my_kwarg}', 'this is', my_kwarg='no fun')
        <Record CRITICAL 'failure'>
        >>> record.message
        u'important_task failure: this is no fun'
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
        return self._exception(None, message, a, kw)

    def _exception(self, exc_info, message, fargs, data):
        if not exc_info:
            exc_info = sys.exc_info()
        try:
            exc_type, exc_val, exc_tb = exc_info
        except Exception:
            exc_type, exc_val, exc_tb = (None, None, None)
        exc_type = exc_type or DefaultException

        # have to capture the time now in case the on_exception sinks
        # take their sweet time
        ctime = time.time()

        self.logger.on_exception(self, exc_type, exc_val, exc_tb)

        exc_info = ExceptionInfo.from_exc_info(exc_type, exc_val, exc_tb)
        if not message:
            message = '%s raised exception: %r' % (self.name, exc_val)
        return self._complete('exception', message, fargs, data,
                              ctime, exc_info)

    def _complete(self, status, message, fargs, data,
                  ctime=None, exc_info=None):
        self.data_map.update(data)
        if ctime is not None:
            end_time = ctime
        elif self._is_trans:
            end_time = time.time()
        else:
            end_time = self.begin_time

        message = to_unicode(message)
        self.complete_record = CompleteRecord(self, end_time, message,
                                              fargs, status, exc_info)

        if not self._defer_publish and self.logger:
            self.logger.on_complete(self.complete_record)

        return self

    def __enter__(self):
        self._is_trans = self._defer_publish = True
        self.logger.on_begin(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._defer_publish = False
        if exc_type:
            # try:  # TODO: uncomment
            self._exception(exc_type, exc_val, exc_tb, message=None)
            # except Exception:
            #    # TODO: something? grasshopper mode maybe.
            #    pass
        elif not self.complete_record:
            self.success()

        self.logger.on_complete(self.complete_record)

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
        if self.begin_record:
            return time.time() - self.begin_record.create_time
        return 0.0

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


class SubRecord(object):
    def __getitem__(self, key):
        return self.root_record[key]

    # TODO
    @property
    def message(self):
        raw_message = self.raw_message
        if raw_message is None:
            return None

        if '{' not in raw_message:  # yay premature optimization
            self._message = raw_message
        else:
            # TODO: Formatter cache
            fmtr = Formatter(raw_message, quoter=False)
            self._message = fmtr.format_record(self.root_record, self.fargs)
        return self._message


class BeginRecord(object):
    def __init__(self, root_record, ctime, raw_message, fargs):
        self.root_record = root_record
        self.create_time = ctime
        self.raw_message = raw_message
        self.fargs = fargs
        self.create_time = ctime


class CompleteRecord(object):
    def __init__(self, root_record, ctime, raw_message, fargs, status,
                 exc_info=None):
        self.root_record = root_record
        self.create_time = ctime
        self.raw_message = raw_message
        self.fargs = fargs
        self.status = status
        self.exc_info = exc_info


class WarnRecord(object):
    def __init__(self, root_record, ctime, raw_message, fargs):
        self.root_record = root_record
        self.create_time = ctime
        self.raw_message = raw_message
        self.fargs = fargs


"""What to do on multiple begins and multiple completes?

If a record is atomic (i.e., never entered/begun), then should it fire
a logger on_begin? Leaning no.

Things that normally change on a Record currently:

 - Status
 - Message
 - Extras

Things which are populated:

 - end_time
 - duration

"""
