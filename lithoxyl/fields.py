# -*- coding: utf-8 -*-
"""Lithoxyl comes with many built-in format *fields* meant to be used
with the standard :class:`~lithoxyl.logger.Logger` and
:class:`~lithoxyl.record.Record`. Sinks can take advantage of these
with the :class:`~lithoxyl.formatters.Formatter` type or subtypes.


"""
# NOTE: docstring table needs slashes double escaped. Also, newline literals "\n" removed.

# TODO: exc_repr field

import os
import time
import json
import datetime

from timeutils import UTC, LocalTZ
from formatutils import BaseFormatField

from common import IMPORT_TIME

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


class FormatField(BaseFormatField):
    """FormatFields specify whether or not they are *quoted* (i.e., whether
    or not values will contain whitespace), but not the exact method
    for their quoting. That aspect is reserved for the Formatter.
    """

    def __init__(self, fname, fspec='s',
                 getter=None, default=None, quote=None):
        # TODO: is default necessary here? Formatters should control
        # defaults, like quotes
        super(FormatField, self).__init__(fname, fspec)
        self.default = default
        self.getter = getter
        if quote is None:
            # numeric fields should appear without quotes
            numeric = issubclass(self.type_func, (int, float))
            quote = not numeric
        self.quote = quote


# default, fmt_specs
FF = FormatField
BASIC_FIELDS = [FF('logger_name', 's', lambda r: r.logger.name),
                FF('logger_id', 'd', lambda r: r.logger.logger_id),
                FF('record_name', 's', lambda r: r.name),
                FF('record_id', 'd', lambda r: r.record_id),
                FF('status_str', 's', lambda r: r.status, quote=False),
                FF('status_char', 's', lambda r: r.status_char, quote=False),
                FF('warn_char', 's', lambda r: r.warn_char, quote=False),
                FF('level_name', 's', lambda r: r.level_name, quote=False),
                FF('extras', 's', lambda r: json.dumps(r.extras, sort_keys=True), quote=False),
                FF('level_name_upper', 's', lambda r: r.level_name.upper(), quote=False),
                FF('level_char', 's', lambda r: r.level_name.upper()[0], quote=False),
                FF('level_number', 'd', lambda r: r.level._value),
                FF('begin_message', 's', lambda r: r.begin_record.message),
                FF('begin_raw_message', 's', lambda r: r.begin_record.raw_message),
                FF('end_message', 's', lambda r: r.complete_record.message),
                FF('end_raw_message', 's', lambda r: r.complete_record.raw_message),
                FF('begin_timestamp', '.14g', lambda r: r.begin_time),
                FF('end_timestamp', '.14g', lambda r: r.end_time),
                FF('duration_secs', '.3f', lambda r: r.duration),
                FF('duration_msecs', '.3f', lambda r: r.duration * 1000.0),
                FF('module_name', 's', lambda r: r.callpoint.module_name),
                FF('module_path', 's', lambda r: r.callpoint.module_path),
                FF('func_name', 's', lambda r: r.callpoint.func_name, quote=False),
                FF('line_number', 'd', lambda r: r.callpoint.lineno),
                FF('exc_type', 's', lambda r: r.exc_info.exc_type, quote=False),
                FF('exc_message', 's', lambda r: r.exc_info.exc_msg),
                FF('exc_tb_str', 's', lambda r: str(r.exc_info.tb_info)),
                FF('exc_tb_list', 's', lambda r: r.exc_info.tb_info.frames),
                FF('process_id', 'd', lambda r: os.getpid())]

# ISO8601 and variants. combinations of:
#   * begin/end
#   * UTC/Local
#   * with/without milliseconds
#   * with/without timezone (_noms variants have textual timezone)
# TODO: rename to just ISO
ISO8601_FIELDS = [
    FF('begin_iso8601', 's',
       lambda r: timestamp2iso8601(r.root.begin_record.ctime)),
    FF('end_iso8601', 's',
       lambda r: timestamp2iso8601(r.root.complete_record.ctime)),
    FF('begin_iso8601_notz', 's',
       lambda r: timestamp2iso8601(r.root.begin_record.ctime,
                                   with_tz=False)),
    FF('end_iso8601_notz', 's',
       lambda r: timestamp2iso8601(r.root.complete_record.ctime,
                                   with_tz=False)),
    FF('begin_local_iso8601', 's',
       lambda r: timestamp2iso8601(r.root.begin_record.ctime,
                                   local=True)),
    FF('end_local_iso8601', 's',
       lambda r: timestamp2iso8601(r.root.complete_record.ctime,
                                   local=True)),
    FF('begin_local_iso8601_notz', 's',
       lambda r: timestamp2iso8601(r.root.begin_record.ctime,
                                   local=True, with_tz=False)),
    FF('end_local_iso8601_notz', 's',
       lambda r: timestamp2iso8601(r.root.complete_record.ctime,
                                   local=True, with_tz=False)),
    FF('begin_local_iso8601_noms', 's',
       lambda r: timestamp2iso8601_noms(r.root.begin_record.ctime,
                                        local=True)),
    FF('end_local_iso8601_noms', 's',
       lambda r: timestamp2iso8601_noms(r.root.complete_record.ctime,
                                        local=True)),
    FF('begin_local_iso8601_noms_notz', 's',
       lambda r: timestamp2iso8601_noms(r.root.begin_record.ctime,
                                        local=True, with_tz=False)),
    FF('end_local_iso8601_noms_notz', 's',
       lambda r: timestamp2iso8601_noms(r.root.complete_record.ctime,
                                        local=True, with_tz=False))]

# using the T separator means no whitespace and thus no quoting
for f in ISO8601_FIELDS:
    f.quote = False


DELTA_FIELDS = [
    FF('import_delta', '0.6f', lambda r: r.ctime - IMPORT_TIME),
    FF('import_delta_ms', '0.4f', lambda r: (r.ctime - IMPORT_TIME) * 1000)]


for f in BASIC_FIELDS:
    register_builtin_field(f)
for f in ISO8601_FIELDS:
    register_builtin_field(f)
for f in DELTA_FIELDS:
    register_builtin_field(f)

del f
