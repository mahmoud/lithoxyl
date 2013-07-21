# -*- coding: utf-8 -*-

from logger import Record, DEBUG
from formatters import Formatter

template = ('{start_timestamp} - {start_local_iso8601} - {start_iso8601}'
            ' - {logger_name} - {record_status} - {record_name}')


def test_formatter_basic():
    riker = Record('hello_thomas', DEBUG).success('')
    forming = Formatter(template)
    output = forming.format_record(riker)
    assert output.endswith('"" - success - "hello_thomas"')
