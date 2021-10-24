# -*- coding: utf-8 -*-

from __future__ import absolute_import

import sys

from lithoxyl import DeferredValue
from lithoxyl.logger import Logger, Action
from lithoxyl.sensible import SensibleFormatter as SF
from lithoxyl.sensible import timestamp2iso8601_noms, timestamp2iso8601

IS_PY3 = sys.version_info[0] == 3

template = ('{status_char}{action_warn_char}{begin_timestamp}'
            ' - {iso_begin_local} - {iso_begin}'
            ' - {logger_name} - {status_str} - {action_name}')


t_log = Logger('1off')
t_riker = Action(t_log, 'DEBUG', 'Riker').success('Hello, Thomas.')

ACTS = [t_riker]


TCS = [[('{logger_name}', '"1off"'),
        ('{status_str}', 'success'),
        ('{level_number}', '20'),
        ('{action_name}', '"Riker"'),
        ('{end_message}', '"Hello, Thomas."')]
       ]


def test_formatter_basic():
    forming = SF(template)
    output = forming.on_end(t_riker.end_event)
    expected = '"1off" - success - "Riker"'
    print(output)
    assert output[-len(expected):] == expected

    act = Action(t_log, 'DEBUG', 'Wharf')
    robf = SF(template)
    act.success('Mr. Wolf')
    ret = robf.on_end(act.end_event)
    print(ret)
    return ret


def test_individual_fields():
    for action, field_pairs in zip(ACTS, TCS):
        for field_tmpl, result in field_pairs:
            forming = SF(field_tmpl)
            output = forming.on_end(action.end_event)
            assert output == result
    return


def test_deferred():
    DV = DeferredValue
    expensive_ops = [(lambda: 5, '"oh, 5"'),
                     (lambda: 'hi', '"oh, hi"'),
                     (lambda: 2.0, '"oh, 2.0"')]
    formatter = SF('{end_message}')

    for eo, expected in expensive_ops:
        act = Action(t_log, 'DEBUG', 'spendy').success('oh, {dv}', dv=DV(eo))
        output = formatter.on_end(act.end_event)
        assert output == expected
    return


def test_timestamp_fmt():
    ts = 1635115925.0000000

    combos = [((timestamp2iso8601, True, True), "2021-10-24T15:52:05.000000-0700"),
              ((timestamp2iso8601, True, False), "2021-10-24T15:52:05.000000"),
              ((timestamp2iso8601, False, True), "2021-10-24T22:52:05.000000+0000"),
              ((timestamp2iso8601, False, False), "2021-10-24T22:52:05.000000"),
              ((timestamp2iso8601_noms, True, False), "2021-10-24T15:52:05"),
              ((timestamp2iso8601_noms, False, False), "2021-10-24T22:52:05"),]

    if IS_PY3:
        combos.extend([
            ((timestamp2iso8601_noms, False, True), "2021-10-24T22:52:05+0000"),
            ((timestamp2iso8601_noms, True, True), "2021-10-24T15:52:05-0700")
        ])


    for (func, local, with_tz), expected in combos:
        assert func(ts, local=local, with_tz=with_tz) == expected

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
