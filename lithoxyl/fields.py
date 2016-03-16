# -*- coding: utf-8 -*-
"""Lithoxyl comes with many built-in format *fields* meant to be used
with the standard :class:`~lithoxyl.logger.Logger` and
:class:`~lithoxyl.record.Record`. Sinks can take advantage of these
with the :class:`~lithoxyl.sensible.SensibleFormatter` type or subtypes.
"""
# NOTE: docstring table needs slashes double escaped. Also, newline
# literals "\n" removed.

# TODO: exc_repr field

import os
import time
import json
import datetime

from boltons.timeutils import UTC, LocalTZ
from boltons.formatutils import BaseFormatField

from lithoxyl.common import IMPORT_TIME

FIELD_MAP = {}
BUILTIN_FIELD_MAP = {}  # populated below


def register_builtin_field(field):
    register_field(field)
    BUILTIN_FIELD_MAP[field.fname] = field


def register_field(field):
    FIELD_MAP[field.fname] = field


def timestamp2iso8601_noms(timestamp, local=False, with_tz=True):
    """
    with time.strftime(), one would have to do fractional
    seconds/milliseconds manually, because the timetuple used doesn't
    include data necessary to support the %f flag.

    This function is about twice as fast as datetime.strftime(),
    however. That's nothing compared to time.time()
    vs. datetime.now(), which is two orders of magnitude faster.
    """
    if with_tz:
        tformat = '%Y-%m-%dT%H:%M:%S %Z'
    else:
        tformat = '%Y-%m-%dT%H:%M:%S'
    if local:
        tstruct = time.localtime(timestamp)
    else:
        tstruct = time.gmtime(timestamp)
    return time.strftime(tformat, tstruct)


def timestamp2iso8601(timestamp, local=False, with_tz=True, tformat=None):
    if with_tz:
        tformat = tformat or '%Y-%m-%dT%H:%M:%S.%f%z'
    else:
        tformat = tformat or '%Y-%m-%dT%H:%M:%S.%f'
    if local:
        dt = datetime.datetime.fromtimestamp(timestamp, tz=LocalTZ)
    else:
        dt = datetime.datetime.fromtimestamp(timestamp, tz=UTC)
    return dt.strftime(tformat)


class SensibleField(BaseFormatField):
    """FormatFields specify whether or not they should be *quoted* (i.e.,
    whether or not values will contain whitespace or other
    delimiters), but not the exact method for their quoting. That
    aspect is reserved for the Formatter.

    """

    def __init__(self, fname, fspec='s', getter=None, **kwargs):
        quote = kwargs.pop('quote', None)
        if kwargs:
            raise TypeError('unexpected keyword arguments: %r' % kwargs.keys())
        super(SensibleField, self).__init__(fname, fspec)
        self.getter = getter
        if quote is None:
            # numeric fields should appear without quotes
            numeric = issubclass(self.type_func, (int, float))
            quote = not numeric
        self.quote = quote


# default, fmt_specs
_SF = SensibleField
BASIC_FIELDS = [_SF('logger_name', 's', lambda e: e.logger.name),
                _SF('logger_id', 'd', lambda e: e.logger.logger_id),
                _SF('record_name', 's', lambda e: e.name),
                _SF('record_id', 'd', lambda e: e.record_id),
                _SF('status_str', 's', lambda e: e.status, quote=False),
                _SF('status_char', 's', lambda e: e.status_char, quote=False),
                _SF('warn_char', 's', lambda e: e.warn_char, quote=False),
                _SF('level_name', 's', lambda e: e.level_name, quote=False),
                _SF('data_map', 's', lambda e: json.dumps(e.record.data_map, sort_keys=True), quote=False),
                _SF('level_name_upper', 's', lambda e: e.level_name.upper(), quote=False),
                _SF('level_char', 's', lambda e: e.level_name.upper()[0], quote=False),
                _SF('level_number', 'd', lambda e: e.level._value),
                _SF('begin_message', 's', lambda e: e.begin_event.message),
                _SF('begin_raw_message', 's', lambda e: e.begin_event.raw_message),
                _SF('end_message', 's', lambda e: e.complete_event.message),
                _SF('end_raw_message', 's', lambda e: e.complete_event.raw_message),
                _SF('begin_timestamp', '.14g', lambda e: e.begin_time),
                _SF('end_timestamp', '.14g', lambda e: e.end_time),
                _SF('duration_secs', '.3f', lambda e: e.duration),
                _SF('duration_msecs', '.3f', lambda e: e.duration * 1000.0),
                _SF('module_name', 's', lambda e: e.callpoint.module_name),
                _SF('module_path', 's', lambda e: e.callpoint.module_path),
                _SF('func_name', 's', lambda e: e.callpoint.func_name, quote=False),
                _SF('line_number', 'd', lambda e: e.callpoint.lineno),
                _SF('exc_type', 's', lambda e: e.exc_info.exc_type, quote=False),
                _SF('exc_message', 's', lambda e: e.exc_info.exc_msg),
                _SF('exc_tb_str', 's', lambda e: str(e.exc_info.tb_info)),
                _SF('exc_tb_list', 's', lambda e: e.exc_info.tb_info.frames),
                _SF('process_id', 'd', lambda e: os.getpid())]

# ISO8601 and variants. combinations of:
#   * begin/end
#   * UTC/Local
#   * with/without milliseconds
#   * with/without timezone (_noms variants have textual timezone)
# TODO: rename to just ISO
ISO8601_FIELDS = [
    _SF('begin_iso8601', 's',
        lambda e: timestamp2iso8601(e.record.begin_event.ctime)),
    _SF('end_iso8601', 's',
        lambda e: timestamp2iso8601(e.record.complete_event.ctime)),
    _SF('begin_iso8601_notz', 's',
        lambda e: timestamp2iso8601(e.record.begin_event.ctime,
                                    with_tz=False)),
    _SF('end_iso8601_notz', 's',
        lambda e: timestamp2iso8601(e.record.complete_event.ctime,
                                    with_tz=False)),
    _SF('begin_local_iso8601', 's',
        lambda e: timestamp2iso8601(e.record.begin_event.ctime,
                                    local=True)),
    _SF('end_local_iso8601', 's',
        lambda e: timestamp2iso8601(e.record.complete_event.ctime,
                                    local=True)),
    _SF('begin_local_iso8601_notz', 's',
        lambda e: timestamp2iso8601(e.record.begin_event.ctime,
                                    local=True, with_tz=False)),
    _SF('end_local_iso8601_notz', 's',
        lambda e: timestamp2iso8601(e.record.complete_event.ctime,
                                    local=True, with_tz=False)),
    _SF('begin_local_iso8601_noms', 's',
        lambda e: timestamp2iso8601_noms(e.record.begin_event.ctime,
                                         local=True)),
    _SF('end_local_iso8601_noms', 's',
        lambda e: timestamp2iso8601_noms(e.record.complete_event.ctime,
                                         local=True)),
    _SF('begin_local_iso8601_noms_notz', 's',
        lambda e: timestamp2iso8601_noms(e.record.begin_event.ctime,
                                         local=True, with_tz=False)),
    _SF('end_local_iso8601_noms_notz', 's',
        lambda e: timestamp2iso8601_noms(e.record.complete_event.ctime,
                                         local=True, with_tz=False))]

# using the T separator means no whitespace and thus no quoting
for f in ISO8601_FIELDS:
    f.quote = False


DELTA_FIELDS = [
    _SF('import_delta', '0.6f', lambda e: e.ctime - IMPORT_TIME),
    _SF('import_delta_ms', '0.4f', lambda e: (e.ctime - IMPORT_TIME) * 1000)]


for f in BASIC_FIELDS:
    register_builtin_field(f)
for f in ISO8601_FIELDS:
    register_builtin_field(f)
for f in DELTA_FIELDS:
    register_builtin_field(f)

del f
