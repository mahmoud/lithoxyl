# -*- coding: utf-8 -*-

from __future__ import absolute_import
import errno

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
                        filters=[SensibleFilter(exception=False)])
    logger = Logger('excelsilog', [sink])
    with logger.info('A for Effort', reraise=False) as tr:
        print(tr)
        raise ValueError('E for Exception')
    return


def test_stale_stream(tmpdir):
    # make mock filestream with write/flush that goes stale after 100 writes
    # create logger with stream emitter to mocked file stream

    class StalewardFile(object):
        def __init__(self, wrapped):
            self._write_count = 0
            self.wrapped = wrapped

        def write(self, *a, **kw):
            self._write_count += 1
            if self._write_count > 100:
                exc = IOError('stale file handle')
                exc.errno = errno.ESTALE
                self.close()
                raise exc
            return self.wrapped.write(*a, **kw)

        def __getattr__(self, name):
            return getattr(self.wrapped, name)

    file_path = '%s/not_always_fresh.log' % (tmpdir,)
    stale_file_obj = StalewardFile(open(file_path, 'wb'))
    emitter = StreamEmitter(stale_file_obj)

    sink = SensibleSink(SF('{status_char} - {iso_end}'), emitter,
                        filters=[SensibleFilter(success=True)])
    logger = Logger('excelsilog', [sink])

    assert emitter.stream is stale_file_obj

    for i in range(200):
        logger.info('yay').success()

    lines = open(file_path).read().splitlines()
    assert len(lines) == 200
    assert len(lines[0]) == len(lines[-1])
    assert stale_file_obj.closed
    assert emitter.stream is not stale_file_obj
