# -*- coding: utf-8 -*-

from logger import Record, DEBUG
from formatters import Formatter

template = ('{start_timestamp} - {start_local_iso8601} - {start_iso8601}'
            ' - {logger_name} - {record_status} - {record_name}')


RECS = [Record('Riker', DEBUG).success('Hello, Thomas.')]


TCS = [[('{logger_name}', '""'),
        ('{record_status}', 'success'),
        ('{level_number}', '20'),
        ('{record_name}', '"Riker"'),
        ('{message}', '"Hello, Thomas."')]
       ]


def test_formatter_basic():
    riker = Record('hello_thomas', DEBUG).success('')
    forming = Formatter(template)
    output = forming.format_record(riker)
    assert output.endswith('"" - success - "hello_thomas"')


def test_individual_fields():
    for record, field_pairs in zip(RECS, TCS):
        for field_tmpl, result in field_pairs:
            forming = Formatter(field_tmpl)
            output = forming.format_record(record)
            assert output == result
    return
