# -*- coding: utf-8 -*-
"""Lithoxyl comes with many built-in format *fields* meant to be used
with the standard :class:`~lithoxyl.logger.Logger` and
:class:`~lithoxyl.record.Record`. Sinks can take advantage of these
with the :class:`~lithoxyl.formatters.Formatter` type or subtypes.

General Fields
--------------

    +----------------------+-----------------------------------------------+----------------------------------+----------+
    | Name                 | Example                                       | Description                      | Quoted   |
    +======================+===============================================+==================================+==========+
    | ``logger_name``      | ``"test_logger"``                             | X                              X | Y        |
    +----------------------+-----------------------------------------------+----------------------------------+----------+
    | ``logger_id``        | ``139890693478288``                           | X                              X |          |
    +----------------------+-----------------------------------------------+----------------------------------+----------+
    | ``record_name``      | ``"test_task"``                               | X                              X | Y        |
    +----------------------+-----------------------------------------------+----------------------------------+----------+
    | ``record_id``        | ``139890664630288``                           | X                              X |          |
    +----------------------+-----------------------------------------------+----------------------------------+----------+
    | ``status_str``       | ``exception``                                 | X                              X |          |
    +----------------------+-----------------------------------------------+----------------------------------+----------+
    | ``status_char``      | ``E``                                         | X                              X |          |
    +----------------------+-----------------------------------------------+----------------------------------+----------+
    | ``warn_char``        | ``W``                                         | X                              X |          |
    +----------------------+-----------------------------------------------+----------------------------------+----------+
    | ``level_name``       | ``critical``                                  | X                              X |          |
    +----------------------+-----------------------------------------------+----------------------------------+----------+
    | ``extras``           | ``{"item": "my_item"}``                       | X                              X |          |
    +----------------------+-----------------------------------------------+----------------------------------+----------+
    | ``level_name_upper`` | ``CRITICAL``                                  | X                              X |          |
    +----------------------+-----------------------------------------------+----------------------------------+----------+
    | ``level_number``     | ``90``                                        | X                              X |          |
    +----------------------+-----------------------------------------------+----------------------------------+----------+
    | ``message``          | ``"test_task raised ... ue for my_item',)"``  | X                              X | Y        |
    +----------------------+-----------------------------------------------+----------------------------------+----------+
    | ``raw_message``      | ``"test_task raised ... lue for {item}',)"``  | X                              X | Y        |
    +----------------------+-----------------------------------------------+----------------------------------+----------+
    | ``begin_timestamp``  | ``1429320301.9148``                           | X                              X |          |
    +----------------------+-----------------------------------------------+----------------------------------+----------+
    | ``end_timestamp``    | ``1429320302.6157``                           | X                              X |          |
    +----------------------+-----------------------------------------------+----------------------------------+----------+
    | ``duration_secs``    | ``0.701``                                     | X                              X |          |
    +----------------------+-----------------------------------------------+----------------------------------+----------+
    | ``duration_msecs``   | ``700.887``                                   | X                              X |          |
    +----------------------+-----------------------------------------------+----------------------------------+----------+
    | ``module_name``      | ``"__main__"``                                | X                              X | Y        |
    +----------------------+-----------------------------------------------+----------------------------------+----------+
    | ``module_path``      | ``"gen_field_table.py"``                      | X                              X | Y        |
    +----------------------+-----------------------------------------------+----------------------------------+----------+
    | ``func_name``        | ``get_test_record``                           | X                              X |          |
    +----------------------+-----------------------------------------------+----------------------------------+----------+
    | ``line_number``      | ``27``                                        | X                              X |          |
    +----------------------+-----------------------------------------------+----------------------------------+----------+
    | ``exc_type``         | ``ValueError``                                | X                              X |          |
    +----------------------+-----------------------------------------------+----------------------------------+----------+
    | ``exc_message``      | ``"unexpected value for {item}"``             | X                              X | Y        |
    +----------------------+-----------------------------------------------+----------------------------------+----------+
    | ``exc_tb_str``       | ``"Traceback (most r ... ue for {item}')"``   | X                              X | Y        |
    +----------------------+-----------------------------------------------+----------------------------------+----------+
    | ``exc_tb_list``      | ``"[Callpoint('get_t ... for {item}')\\")]"``  | X                              X | Y        |
    +----------------------+-----------------------------------------------+----------------------------------+----------+
    | ``process_id``       | ``{process_id}``                              | X                              X |          |
    +----------------------+-----------------------------------------------+----------------------------------+----------+


Timestamp Fields
----------------

    +-----------------------------------+-------------------------------------+----------------------------------+
    | Name                              | Example                             | Description                      |
    +===================================+=====================================+==================================+
    | ``begin_iso8601``                 | ``2015-04-18T01:25:01.914817+0000`` | X                              X |
    +-----------------------------------+-------------------------------------+----------------------------------+
    | ``end_iso8601``                   | ``2015-04-18T01:25:02.615704+0000`` | X                              X |
    +-----------------------------------+-------------------------------------+----------------------------------+
    | ``begin_iso8601_notz``            | ``2015-04-18T01:25:01.914817``      | X                              X |
    +-----------------------------------+-------------------------------------+----------------------------------+
    | ``end_iso8601_notz``              | ``2015-04-18T01:25:02.615704``      | X                              X |
    +-----------------------------------+-------------------------------------+----------------------------------+
    | ``begin_local_iso8601``           | ``2015-04-17T18:25:01.914817-0700`` | X                              X |
    +-----------------------------------+-------------------------------------+----------------------------------+
    | ``end_local_iso8601``             | ``2015-04-17T18:25:02.615704-0700`` | X                              X |
    +-----------------------------------+-------------------------------------+----------------------------------+
    | ``begin_local_iso8601_notz``      | ``2015-04-17T18:25:01.914817``      | X                              X |
    +-----------------------------------+-------------------------------------+----------------------------------+
    | ``end_local_iso8601_notz``        | ``2015-04-17T18:25:02.615704``      | X                              X |
    +-----------------------------------+-------------------------------------+----------------------------------+
    | ``begin_local_iso8601_noms``      | ``2015-04-17 18:25:01 PDT``         | X                              X |
    +-----------------------------------+-------------------------------------+----------------------------------+
    | ``end_local_iso8601_noms``        | ``2015-04-17 18:25:02 PDT``         | X                              X |
    +-----------------------------------+-------------------------------------+----------------------------------+
    | ``begin_local_iso8601_noms_notz`` | ``2015-04-17 18:25:01``             | X                              X |
    +-----------------------------------+-------------------------------------+----------------------------------+
    | ``end_local_iso8601_noms_notz``   | ``2015-04-17 18:25:02``             | X                              X |
    +-----------------------------------+-------------------------------------+----------------------------------+

"""
# NOTE: docstring table needs slashes double escaped. Also, newline literals "\n" removed.

# TODO: should record_id be combined with logger_id? loggers are not
# ephemeral, but records are; there are chances of id reuse.

import time
import json
import datetime

from tzutils import UTC, LocalTZ
from formatutils import BaseFormatField

BUILTIN_FIELD_MAP = {}  # populated below


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
        tformat = '%Y-%m-%d %H:%M:%S %Z'
    else:
        tformat = '%Y-%m-%d %H:%M:%S'
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
                FF('logger_id', 'd', lambda r: id(r.logger)),  # TODO
                FF('record_name', 's', lambda r: r.name),
                FF('record_id', 'd', lambda r: id(r)),  # TODO
                FF('status_str', 's', lambda r: r.status, quote=False),
                FF('status_char', 's', lambda r: r.status_char, quote=False),
                FF('warn_char', 's', lambda r: r.warn_char, quote=False),
                FF('level_name', 's', lambda r: r.level_name, quote=False),
                FF('extras', 's', lambda r: json.dumps(r.extras, sort_keys=True), quote=False),
                FF('level_name_upper', 's', lambda r: r.level_name.upper(), quote=False),
                FF('level_char', 's', lambda r: r.level_name.upper()[0], quote=False),
                FF('level_number', 'd', lambda r: r.level._value),
                FF('message', 's', lambda r: r.message),
                FF('raw_message', 's', lambda r: r.raw_message),
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
                FF('process_id', 'd', lambda r: 'TODO')]

# ISO8601 and variants. combinations of:
#   * begin/end
#   * UTC/Local
#   * with/without milliseconds
#   * with/without timezone (_noms variants have textual timezone)
ISO8601_FIELDS = [
        FF('begin_iso8601', 's', lambda r: timestamp2iso8601(r.begin_time)),
        FF('end_iso8601', 's', lambda r: timestamp2iso8601(r.end_time)),
        FF('begin_iso8601_notz', 's',
           lambda r: timestamp2iso8601(r.begin_time, with_tz=False)),
        FF('end_iso8601_notz', 's',
           lambda r: timestamp2iso8601(r.end_time, with_tz=False)),
        FF('begin_local_iso8601', 's',
           lambda r: timestamp2iso8601(r.begin_time, local=True)),
        FF('end_local_iso8601', 's',
           lambda r: timestamp2iso8601(r.end_time, local=True)),
        FF('begin_local_iso8601_notz', 's',
           lambda r: timestamp2iso8601(r.begin_time, local=True, with_tz=False)),
        FF('end_local_iso8601_notz', 's',
           lambda r: timestamp2iso8601(r.end_time, local=True, with_tz=False)),
        FF('begin_local_iso8601_noms', 's',
           lambda r: timestamp2iso8601_noms(r.begin_time, local=True)),
        FF('end_local_iso8601_noms', 's',
           lambda r: timestamp2iso8601_noms(r.end_time, local=True)),
        FF('begin_local_iso8601_noms_notz', 's',
           lambda r: timestamp2iso8601_noms(r.begin_time, local=True, with_tz=False)),
        FF('end_local_iso8601_noms_notz', 's',
           lambda r: timestamp2iso8601_noms(r.end_time, local=True, with_tz=False))]

# using the T separator means no whitespace and thus no quoting
for f in ISO8601_FIELDS:
    f.quote = False


def register_builtin_field(f):
    BUILTIN_FIELD_MAP[f.fname] = f


for f in BASIC_FIELDS:
    register_builtin_field(f)
for f in ISO8601_FIELDS:
    register_builtin_field(f)

del f
