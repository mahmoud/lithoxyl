# -*- coding: utf-8 -*-

from logger import Record, DEBUG
from formatters import Formatter, Templette

template = ('{start_timestamp} - {start_local_iso8601} - {start_iso8601}'
            ' - {logger_name} - {record_status} - {record_name}')


RECS = [Record('Riker', DEBUG).success('Hello, Thomas.')]


TCS = [[('{logger_name}', '{logger_name}'),
        ('{record_status}', 'success'),
        ('{level_number}', '20'),
        ('{record_name}', '"Riker"'),
        ('{message}', '"Hello, Thomas."')]
       ]


def test_formatter_basic():
    riker = Record('hello_thomas', DEBUG).success('')
    forming = Templette(template)
    output = forming.format_record(riker)
    expected = '{logger_name} - success - "hello_thomas"'
    assert output[-len(expected):] == expected


def test_individual_fields():
    for record, field_pairs in zip(RECS, TCS):
        for field_tmpl, result in field_pairs:
            forming = Templette(field_tmpl)
            output = forming.format_record(record)
            assert output == result
    return


"""
Formatter tests

* no args/kwargs
* sufficient, correct args/kwargs
* anonymous args
* missing kwarg
* missing arg
* type mismatch args
* type mismatch kwargs
* usage of "builtin" fields
"""


def test_rec_formatter():
    """
    * no args/kwargs
    * sufficient, correct args/kwargs
    * anonymous args
    * missing kwarg
    * missing arg
    * type mismatch args
    * type mismatch kwargs
    * usage of "builtin" fields
    """

    rec = Record('Wharf')
    robf = Templette(template)
    rec.success('Mr. Wolf')
    ret = robf.format_record(rec)
    print ret
    return ret
