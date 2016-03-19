# -*- coding: utf-8 -*-

from lithoxyl import DeferredValue
from lithoxyl.logger import Logger, Record
from lithoxyl.sensible import SensibleFormatter as SF



template = ('{status_char}{record_warn_char}{begin_timestamp}'
            ' - {iso_begin_local} - {iso_begin}'
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
    forming = SF(template)
    output = forming.on_end(t_riker.end_event)
    expected = '"1off" - success - "Riker"'
    print output
    assert output[-len(expected):] == expected

    rec = Record(t_log, 'DEBUG', 'Wharf')
    robf = SF(template)
    rec.success('Mr. Wolf')
    ret = robf.on_end(rec.end_event)
    print ret
    return ret


def test_individual_fields():
    for record, field_pairs in zip(RECS, TCS):
        for field_tmpl, result in field_pairs:
            forming = SF(field_tmpl)
            output = forming.on_end(record.end_event)
            assert output == result
    return


def test_deferred():
    DV = DeferredValue
    expensive_ops = [(lambda: 5, '"oh, 5"'),
                     (lambda: 'hi', '"oh, hi"'),
                     (lambda: 2.0, '"oh, 2.0"')]
    formatter = SF('{end_message}')

    for eo, expected in expensive_ops:
        rec = Record(t_log, 'DEBUG', 'spendy').success('oh, {dv}', dv=DV(eo))
        output = formatter.on_end(rec.end_event)
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
