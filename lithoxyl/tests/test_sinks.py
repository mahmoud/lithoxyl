import io
import json
import errno
import sys
import time

import pytest

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



def test_dev_debug_sink_basic():
    from lithoxyl.sinks import DevDebugSink
    sink = DevDebugSink()
    assert sink.reraise is False
    assert sink.post_mortem is False


def test_dev_debug_sink_reraise():
    from lithoxyl.sinks import DevDebugSink
    sink = DevDebugSink(reraise=True)
    assert sink.reraise is Exception
    try:
        raise ValueError('test')
    except ValueError:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        with pytest.raises(ValueError, match='test'):
            sink.on_exception(None, exc_type, exc_obj, exc_tb)


def test_dev_debug_sink_post_mortem():
    from lithoxyl.sinks import DevDebugSink
    from unittest.mock import patch
    sink = DevDebugSink(post_mortem=True)
    assert sink.post_mortem is Exception
    try:
        raise RuntimeError('pm')
    except RuntimeError:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        with patch('lithoxyl.sinks.pdb') as mock_pdb:
            sink.on_exception(None, exc_type, exc_obj, exc_tb)
            mock_pdb.post_mortem.assert_called_once()


def test_rate_accumulator_repr():
    from lithoxyl.sinks import RateAccumulator
    ra = RateAccumulator()
    assert 'RateAccumulator' in repr(ra)
    assert 'rate=' in repr(ra)


def test_rate_accumulator_empty_norm_times():
    from lithoxyl.sinks import RateAccumulator
    ra = RateAccumulator()
    assert ra.get_norm_times() == []


def test_rate_accumulator_get_rate_empty():
    from lithoxyl.sinks import RateAccumulator
    ra = RateAccumulator()
    assert ra.get_rate() == 0.0


def test_rate_accumulator_get_rate_with_data():
    from lithoxyl.sinks import RateAccumulator
    ra = RateAccumulator(sample_size=10)
    base = time.time()
    for i in range(5):
        ra.add(base + i * 0.1)
    rate = ra.get_rate()
    assert rate > 0
    assert ra.total_count == 5
    assert len(ra.get_norm_times()) == 5


def test_rate_accumulator_get_rate_with_start_time():
    from lithoxyl.sinks import RateAccumulator
    ra = RateAccumulator(sample_size=10)
    base = ra.creation_time
    for i in range(5):
        ra.add(base + i * 0.01)
    # start_time after creation_time triggers bisect path
    rate = ra.get_rate(start_time=base + 0.005, end_time=base + 0.05)
    assert rate >= 0
    # Also test the reservoir-exhaustion fallback: start_time far in the future
    rate2 = ra.get_rate(start_time=base + 1.0, end_time=base + 2.0)
    assert rate2 >= 0


def test_rate_sink_basic():
    from lithoxyl.sinks import RateSink
    rs = RateSink()
    log = Logger('rate_test', [rs])
    for i in range(10):
        log.info('task').success()
    rates = rs.get_rates()
    assert '__all__' in rates
    assert rates['__all__'] > 0
    counts = rs.get_total_counts()
    assert counts['__all__'] == 10
    assert 'RateSink' in repr(rs)


def test_rate_sink_max_time():
    from lithoxyl.sinks import RateSink
    rs = RateSink()
    log = Logger('rate_test2', [rs])
    log.info('task').success()
    rates = rs.get_rates(max_time=60)
    assert '__all__' in rates


def test_ewma_sink_basic():
    from lithoxyl.sinks import EWMASink
    es = EWMASink()
    log = Logger('ewma_test', [es])
    with log.info('task') as act:
        pass
    vals = es.get_values()
    assert '__all__' in vals
    assert 'EWMASink' in repr(es)


def test_quantile_sink_basic():
    from lithoxyl.sinks import QuantileSink
    qs = QuantileSink()
    log = Logger('q_test', [qs])
    for i in range(50):
        with log.info('task') as act:
            pass
    d = qs.to_dict()
    assert 'q_test' in d
    assert 'QuantileSink' in repr(qs)


def test_quantile_sink_p2():
    from lithoxyl.sinks import QuantileSink
    qs = QuantileSink(use_p2=True)
    log = Logger('q_test_p2', [qs])
    for i in range(50):
        with log.info('task') as act:
            pass
    d = qs.to_dict()
    assert 'q_test_p2' in d


def test_stream_emitter_non_stream_type_error():
    with pytest.raises(TypeError):
        StreamEmitter(42)


def test_stream_emitter_text_mode_value_error(tmpdir):
    path = '%s/text_mode.log' % (tmpdir,)
    with open(path, 'w') as f:
        with pytest.raises(ValueError, match='binary mode'):
            StreamEmitter(f)


def test_stream_emitter_flush_exception():
    from unittest.mock import MagicMock
    stream = io.BytesIO()
    emitter = StreamEmitter(stream)
    # Mock flush to raise
    stream.flush = MagicMock(side_effect=OSError('flush failed'))
    # flush should swallow the exception (note it, not raise)
    emitter.flush()  # should not raise


def test_file_emitter_close_exception(tmpdir):
    path = '%s/close_exc.log' % (tmpdir,)
    fe = FileEmitter(path)
    # Close the underlying stream first to cause an error on second close
    fe.stream.close()
    fe.stream = None  # set to None to exercise the early return path
    fe.close()  # should not raise (early return)