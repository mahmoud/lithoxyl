# -*- coding: utf-8 -*-

from lithoxyl import (SensibleSink,
                      SensibleFilter,
                      SensibleFormatter as SF,
                      SensibleMessageFormatter as SMF)
from lithoxyl.emitters import StreamEmitter, AggregateEmitter
from lithoxyl.logger import Logger


fmtr = SF('{status_char}{begin_timestamp} - {event_message}')
strm_emtr = StreamEmitter('stderr')
fltr = SensibleFilter('debug')
aggr_emtr = AggregateEmitter()
strm_sink = SensibleSink(formatter=fmtr, emitter=strm_emtr)
fake_sink = SensibleSink(filters=[fltr], formatter=fmtr, emitter=aggr_emtr)


def test_sensible_basic():
    log = Logger('test_ss', [strm_sink, fake_sink])

    print

    log.debug('greet').success('hey')
    assert aggr_emtr.get_entry(-1).startswith('s')

    with log.debug('greet') as t:
        log.comment('a_{}_quick', 'comment')
        assert aggr_emtr.get_entry(-1).startswith('#')
        assert 'a_comment_quick' in aggr_emtr.get_entry(-1)
        t.success('hello')
        t.warn("everything ok?")

    assert aggr_emtr.get_entry(-1).startswith('S')

    with log.debug('greet') as t:
        t.failure('bye')
    assert aggr_emtr.get_entry(-1).startswith('F')

    try:
        with log.debug('greet') as t:
            raise ZeroDivisionError('narwhalbaconderp')
    except Exception:
        pass

    assert aggr_emtr.get_entry(-1).startswith('E')
    assert 'limit=' in repr(aggr_emtr)
    assert aggr_emtr.get_entries()
    aggr_emtr.clear()
    assert not aggr_emtr.get_entries()


def test_bad_encoding():
    try:
        StreamEmitter('stderr', encoding='nope')
    except LookupError:
        assert True
    else:
        assert False


def test_bad_encoding_error_fallback():
    try:
        StreamEmitter('stderr', errors='badvalue')
    except LookupError:
        assert True
    else:
        assert False


def _test_exception():
    _tmpl = ('{iso_end} - {exc_type}: {exc_message}'
             ' - {func_name}:{line_number} - {exc_tb_list}')
    sink = SensibleSink(SF(_tmpl),
                        StreamEmitter('stderr'),
                        filters=[SensibleFilter(exception=0)])
    logger = Logger('excelsilog', [sink])
    with logger.info('A for Effort', reraise=False) as tr:
        print tr
        raise ValueError('E for Exception')
    return
