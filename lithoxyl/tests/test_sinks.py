# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function
import io
import json
import errno

from lithoxyl import (SensibleSink,
                      SensibleFilter,
                      SensibleFormatter as SF,
                      SensibleMessageFormatter as SMF)
from lithoxyl.emitters import StreamEmitter, AggregateEmitter, stream_types, FileEmitter
from lithoxyl.logger import Logger


fmtr = SF('{status_char}{begin_timestamp} - {event_message}')
strm_emtr = StreamEmitter('stderr')
fltr = SensibleFilter('debug')
aggr_emtr = AggregateEmitter()
strm_sink = SensibleSink(formatter=fmtr, emitter=strm_emtr)
fake_sink = SensibleSink(filters=[fltr], formatter=fmtr, emitter=aggr_emtr)


def test_sensible_basic():
    log = Logger('test_ss', [strm_sink, fake_sink])

    log.debug('greet', data={'skey': 'svalue'}).success()
    assert aggr_emtr.get_entry(-1).startswith('s')

    with log.debug('greet') as t:
        log.comment('a_{}_quick', 'comment')
        assert aggr_emtr.get_entry(-1).startswith('#')
        assert 'a_comment_quick' in aggr_emtr.get_entry(-1)
        t.success('hello')
        t.warn("everything ok?")

    assert aggr_emtr.get_entry(-1).startswith('S')

    with log.debug('greet', data={'fkey': 'fval'}) as t:
        t.failure()
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


def test_stale_stream(tmpdir):
    # make mock filestream with write/flush that goes stale after 100 writes
    # create logger with stream emitter to mocked file stream

    class StalewardFile(io.BufferedWriter):
        def __init__(self, wrapped, *a, **kw):
            super(StalewardFile, self).__init__(wrapped, *a, **kw)
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
            print('getting', name)
            return getattr(self.wrapped, name)

    file_path = '%s/not_always_fresh.log' % (tmpdir,)
    wrapped = io.open(file_path, 'wb')
    stale_file_obj = StalewardFile(wrapped)
    emitter = StreamEmitter(stale_file_obj)

    sink = SensibleSink(SF('{status_char} - {iso_end}'), emitter,
                        filters=[SensibleFilter(success=True)])
    assert repr(sink).startswith('<SensibleSink')
    logger = Logger('excelsilog', [sink])

    assert emitter.stream.name is stale_file_obj.name
    first_stream = emitter.stream
    logger.context.note_handlers.append(print)
    for i in range(200):
        logger.info('yay').success()

    lines = open(file_path).read().splitlines()
    assert len(lines) == 200
    assert len(lines[0]) == len(lines[-1])
    assert stale_file_obj.closed
    assert emitter.stream.name is stale_file_obj.name
    assert emitter.stream is not first_stream


def test_stream_emitter(tmpdir):
    def get_bw(base_dir, suffix):
        bw_f = io.open('%s/tmp_%s.txt' % (base_dir, suffix), 'wb')
        bw = bw_f if type(bw_f) is io.BufferedWriter else io.BufferedWriter(bw_f)
        return bw

    def get_stream_lines(stream):
        if getattr(stream, 'name', None):
            contents = open(stream.name, 'rb').read()
        else:
            contents = stream.getvalue()
        contents = contents.decode('utf8')
        return contents.splitlines()

    examples = {
        io.BufferedWriter: get_bw(tmpdir, 'bw'),
        io.RawIOBase: get_bw(tmpdir, 'raw').detach(),
        io.BytesIO: io.BytesIO(),
    }
    try:
        if file in stream_types:
            examples[file] = open('%s/tmp_file.txt' % (tmpdir,), 'wb')  # py2

            import StringIO
            examples[StringIO.StringIO] = StringIO.StringIO()
    except NameError:
        pass  # py3

    passing_types = []

    # import pdb; logger.context.note_handlers.append(lambda x, y: pdb.post_mortem())
    for _type, example_stream in examples.items():
        assert isinstance(example_stream, _type)
        emitter = StreamEmitter(example_stream, encoding='utf8')

        sink = SensibleSink(SF('{status_char} - {iso_end} - {end_message}'), emitter,
                            filters=[SensibleFilter(success=True)])
        logger = Logger('excelsilog', [sink])
        for i in range(201):
            logger.info('action').success('yäy{i}', i=i)

        stream_lines = get_stream_lines(example_stream)
        assert len(stream_lines) == 201
        assert json.dumps(u'yäy0') in stream_lines[0]
        assert json.dumps(u'yäy200') in stream_lines[-1]

        passing_types.append(_type)

    assert set(stream_types) == set(passing_types)


def test_file_emitter(tmpdir):
    path = '%s/log.txt' % (tmpdir,)

    def get_logger(emitter):
        sink = SensibleSink(SF('{status_char} - {iso_end} - {end_message}'), emitter,
                            filters=[SensibleFilter(success=True)])
        return Logger('excelsilog', [sink])

    def _chk_linecount(count):
        assert len(open(path).read().splitlines()) == count

    fe = FileEmitter(path)
    logger = get_logger(fe)

    for i in range(203):
        logger.info('action').success('yäy{i}', i=i)
    _chk_linecount(203)

    fe_over = FileEmitter(path, overwrite=True)
    logger_over = get_logger(fe)

    for i in range(22):
        logger_over.info('action').success('yäy{i}', i=i)
    _chk_linecount(22)

    fe_over.close()  # is close really necessary?
    fe_over.close()

    for i in range(23):
        logger.info('action').success('yäy{i}', i=i)
    _chk_linecount(45)
