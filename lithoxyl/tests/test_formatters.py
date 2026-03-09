import pytest

import datetime
import time

from boltons.timeutils import UTC, LocalTZ

from lithoxyl import DeferredValue
from lithoxyl.logger import Logger, Action
from lithoxyl.sensible import SensibleFormatter as SF
from lithoxyl.sensible import timestamp2iso8601_noms, timestamp2iso8601
from lithoxyl import SensibleSink, SensibleFilter
from lithoxyl.sensible import SensibleMessageFormatter as SMF

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

    # Compute expected local representations dynamically so the test
    # passes regardless of the machine's timezone.
    local_dt = datetime.datetime.fromtimestamp(ts, tz=LocalTZ)
    utc_dt = datetime.datetime.fromtimestamp(ts, tz=UTC)
    local_iso = local_dt.strftime('%Y-%m-%dT%H:%M:%S.%f%z')
    local_iso_noms = local_dt.strftime('%Y-%m-%dT%H:%M:%S')
    local_iso_noms_tz = local_dt.strftime('%Y-%m-%dT%H:%M:%S%z')

    combos = [
        ((timestamp2iso8601, True, True), local_iso),
        ((timestamp2iso8601, True, False), local_dt.strftime('%Y-%m-%dT%H:%M:%S.%f')),
        ((timestamp2iso8601, False, True), "2021-10-24T22:52:05.000000+0000"),
        ((timestamp2iso8601, False, False), "2021-10-24T22:52:05.000000"),
        ((timestamp2iso8601_noms, True, False), local_iso_noms),
        ((timestamp2iso8601_noms, False, False), "2021-10-24T22:52:05"),
        ((timestamp2iso8601_noms, False, True), "2021-10-24T22:52:05+0000"),
        ((timestamp2iso8601_noms, True, True), local_iso_noms_tz),
    ]

    for (func, local, with_tz), expected in combos:
        assert func(ts, local=local, with_tz=with_tz) == expected

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


def test_sensible_sink_single_string_event():
    from lithoxyl.emitters import AggregateEmitter
    emtr = AggregateEmitter()
    sink = SensibleSink(formatter=SF('{status_char}'), emitter=emtr, on='begin')
    log = Logger('ss_test', [sink])
    with log.debug('test') as act:
        act.success()
    # begin event should have been emitted
    assert len(emtr.items) >= 1


def test_sensible_sink_bad_event():
    from lithoxyl.emitters import AggregateEmitter
    with pytest.raises(ValueError, match='unrecognized events'):
        SensibleSink(formatter=SF('{status_char}'), emitter=AggregateEmitter(), on=['bogus'])


def test_sensible_filter_block_comments():
    fltr = SensibleFilter(block_comments=True)
    # on_comment should return False
    assert fltr.on_comment(None) is False


def test_sensible_filter_custom_verbose_flag():
    fltr = SensibleFilter(verbose_flag='custom_verbose')
    # The verbose_check lambda should look for 'custom_verbose' in data_map
    assert fltr.verbose_check is not None


def test_sensible_filter_verbose_begin():
    fltr = SensibleFilter(begin='critical')  # high threshold
    log = Logger('filter_test', [])
    act = log.debug('test')  # debug < critical, should fail base check
    act.begin()
    # Without verbose flag, begin should be filtered
    assert fltr.on_begin(act.begin_event) is False
    # With verbose flag set
    act['verbose'] = True
    assert fltr.on_begin(act.begin_event) is True
    act.success()


def test_sensible_filter_verbose_end():
    fltr = SensibleFilter(success='critical')
    log = Logger('filter_test2', [])
    act = log.debug('test')
    act.begin()
    act.success()
    # success event at debug level < critical threshold
    assert fltr.on_end(act.end_event) is False
    act['verbose'] = True
    assert fltr.on_end(act.end_event) is True


def test_sensible_filter_verbose_warn():
    fltr = SensibleFilter(warn='critical')
    log = Logger('filter_test3', [])
    act = log.debug('test')
    act.begin()
    act.warn('oops')
    assert fltr.on_warn(act.warn_events[0]) is False
    act['verbose'] = True
    assert fltr.on_warn(act.warn_events[0]) is True
    act.success()


def test_sensible_field_unexpected_kwargs():
    from lithoxyl.sensible import SensibleField
    with pytest.raises(TypeError, match='unexpected keyword'):
        SensibleField('x', bogus=True)


def test_smf_quoter_false():
    fmtr = SMF('{status_str}', quoter=False)
    log = Logger('qf_test', [])
    act = log.debug('test')
    act.success()
    result = fmtr.format(act.end_event)
    assert result == 'success'  # no quotes


def test_smf_quoter_invalid():
    with pytest.raises(TypeError, match='expected callable or False'):
        SMF('{status_str}', quoter=42)


def test_smf_defaulter_invalid():
    with pytest.raises(TypeError, match='expected callable for defaulter'):
        SMF('{status_str}', defaulter=42)


def test_formatter_per_event_override():
    fmtr = SF('{status_str}', end='custom {status_str}')
    log = Logger('override_test', [])
    act = log.debug('test')
    act.success()
    result = fmtr.on_end(act.end_event)
    assert 'custom' in result


def test_timestamp_local_notz():
    ts = 1635115925.0
    result = timestamp2iso8601(ts, local=True, with_tz=False)
    assert 'T' in result
    assert '+' not in result  # no timezone


def test_timestamp_noms_local_notz():
    ts = 1635115925.0
    result = timestamp2iso8601_noms(ts, local=True, with_tz=False)
    assert 'T' in result
    assert '.' not in result  # no milliseconds
