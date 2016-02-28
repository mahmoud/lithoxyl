# -*- coding: utf-8 -*-

from lithoxyl.logger import Logger, Record, DEBUG
from lithoxyl.formatters import Formatter
from lithoxyl.formatutils import DeferredValue


template = ('{status_char}{record_warn_char}{begin_timestamp}'
            ' - {begin_local_iso8601} - {begin_iso8601}'
            ' - {logger_name} - {status_str} - {record_name}')


t_log = Logger('1off')
t_riker = Record(t_log, 'DEBUG', 'Riker').success('Hello, Thomas.')

RECS = [t_riker]


TCS = [[('{logger_name}', '"1off"'),
        ('{status_str}', 'success'),
        ('{level_number}', '20'),
        ('{record_name}', '"Riker"'),
        ('{end_message}', '"Hello, Thomas."')]
       ]


def test_formatter_basic():
    forming = Formatter(template)
    output = forming.on_complete(t_riker.complete_record)
    expected = '"1off" - success - "Riker"'
    print output
    assert output[-len(expected):] == expected

    rec = Record(t_log, 'DEBUG', 'Wharf')
    robf = Formatter(template)
    rec.success('Mr. Wolf')
    ret = robf.on_complete(rec.complete_record)
    print ret
    return ret


def test_individual_fields():
    for record, field_pairs in zip(RECS, TCS):
        for field_tmpl, result in field_pairs:
            forming = Formatter(field_tmpl)
            output = forming.on_complete(record.complete_record)
            assert output == result
    return


def test_deferred():
    DV = DeferredValue
    expensive_ops = [(lambda: 5, '"oh, 5"'),
                     (lambda: 'hi', '"oh, hi"'),
                     (lambda: 2.0, '"oh, 2.0"')]
    formatter = Formatter('{end_message}')

    for eo, expected in expensive_ops:
        rec = Record(t_log, 'DEBUG', 'spendy').success('oh, {dv}', dv=DV(eo))
        output = formatter.on_complete(rec.complete_record)
        assert output == expected
    return


"""
Formatter tests todos

* no args/kwargs
* sufficient, correct args/kwargs
* anonymous args
* missing kwarg
* missing arg
* type mismatch args
* type mismatch kwargs
* usage of "builtin" fields
"""
