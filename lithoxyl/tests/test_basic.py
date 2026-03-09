import sys
import time
import json

from lithoxyl.sinks import AggregateSink
from lithoxyl.logger import Logger


def _get_logger():
    acc = AggregateSink()
    return Logger('test_logger', [acc])


def do_debug_act(logger):
    with logger.debug('hi') as act:
        time.sleep(0.01)
        act.success('yay')
    return act


def test_logger_success(act_count=2):
    logger = _get_logger()
    for i in range(act_count):
        do_debug_act(logger)
    assert len(logger.sinks[0].end_events) == act_count
    agg_sink_repr = repr(logger.sinks[0])
    assert 'begins=' in agg_sink_repr
    assert 'begins=0' not in agg_sink_repr

    assert '<Logger' in repr(logger)


def test_callpoint_info():
    log = Logger('test_logger', [])
    act = do_debug_act(log)
    assert act.callpoint.module_name == __name__
    assert act.callpoint.module_path.endswith(__file__)
    assert act.callpoint.func_name == 'do_debug_act'
    assert act.callpoint.lineno > 0
    assert act.callpoint.lasti > 0
    assert repr(act)


def test_guid():
    import string

    log = Logger('test_logger', [])
    act = do_debug_act(log)
    assert act.guid
    assert act.guid.lower() == act.guid
    assert all([c in string.hexdigits for c in act.guid])

    act2 = do_debug_act(log)
    assert act.guid != act2.guid
    assert act.guid < act2.guid  # when int2hexguid_seq is in use


def test_reraise_false():
    logger = _get_logger()
    with logger.debug('hi', reraise=False) as t:
        x
    assert logger.sinks[0].end_events[0].status == 'exception'


def test_reraise_true():
    logger = _get_logger()
    try:
        with logger.debug('hi', reraise=True) as t:
            y
    except NameError:
        assert True
    else:
        assert False, 'should have reraised NameError'


_MSG_ATTRS = ('name', 'level_name', 'status', 'message',
              'begin_time', 'end_time', 'duration')


class SimpleStructuredFileSink(object):
    def __init__(self, fileobj=None):
        self.fileobj = fileobj or sys.stdout

    def on_end(self, event):
        msg_data = dict(event.data_map)
        for attr in _MSG_ATTRS:
            msg_data[attr] = getattr(event, attr, None)
        json_str = json.dumps(msg_data, sort_keys=True)
        self.fileobj.write(json_str)
        self.fileobj.write('\n')


def test_structured(act_count=5):
    acc = SimpleStructuredFileSink()
    log = Logger('test_logger', [acc])
    for i in range(act_count):
        do_debug_act(log)


def test_dup_sink():
    log = Logger('test_exc_logger')
    agg_sink = AggregateSink()

    log.add_sink(agg_sink)
    log.add_sink(agg_sink)

    assert len(log.sinks) == 1


def test_exception():
    log = Logger('test_exc_logger')

    exc_list = []

    class ExcSink(object):
        def on_exception(self, event, etype, eobj, etb):
            exc_list.append(event)

    exc_sink = ExcSink()
    log.add_sink(exc_sink)

    try:
        with log.critical('raise_act'):
            raise RuntimeError('whooops')
    except RuntimeError:
        pass

    assert len(exc_list) == 1
    assert exc_list[0].exc_info.exc_type == 'RuntimeError'


def test_comment():
    log = Logger('test_comment')

    events = []

    class ComSink(object):
        def on_comment(self, event):
            events.append(event)

    log.add_sink(ComSink())

    log.comment('the first')
    log.comment('the second {}', 'commenting')

    assert len(events) == 2
    for event in events:
        assert repr(event).startswith('<')



def test_duration_before_begin():
    log = _get_logger()
    act = log.debug('test')
    # duration before begin should return 0.0
    assert act.duration == 0.0


def test_elapsed_time_before_begin():
    log = _get_logger()
    act = log.debug('test')
    assert act.get_elapsed_time() == 0.0


def test_begin_auto_message():
    log = _get_logger()
    act = log.debug('mytask')
    act.begin()
    assert act.begin_event.raw_message == 'mytask beginning'
    act.success()


def test_success_with_data_no_message():
    log = _get_logger()
    act = log.debug('test', data={'key': 'val'})
    act.success()
    assert 'data_map_repr' in act.end_event.raw_message


def test_failure_with_data_no_message():
    log = _get_logger()
    act = log.debug('test', data={'key': 'val'})
    act.failure()
    assert 'data_map_repr' in act.end_event.raw_message


def test_failure_no_data_no_message():
    log = _get_logger()
    act = log.debug('test')
    act.failure()
    assert 'failed' in act.end_event.raw_message


def test_explicit_parent():
    log = _get_logger()
    parent = log.debug('parent')
    parent.begin()
    child = log.debug('child', parent_action=parent)
    assert child.parent_action is parent
    child.success()
    parent.success()


def test_parent_depth():
    log = _get_logger()
    with log.debug('l1') as a1:
        with log.debug('l2') as a2:
            with log.debug('l3') as a3:
                assert a3.parent_depth >= 2
                a3.success()
            a2.success()
        a1.success()


def test_explicit_exception_call():
    log = _get_logger()
    with log.debug('exc_test', reraise=False) as act:
        try:
            raise RuntimeError('explicit')
        except RuntimeError:
            act.exception('caught it')
    assert act.exc_event is not None
    assert act.exc_event.exc_info.exc_type == 'RuntimeError'


def test_oserror_with_errno():
    log = _get_logger()
    with log.debug('os_test', reraise=False) as act:
        raise OSError(2, 'No such file')
    assert 'errno' in act.end_event.raw_message or 'OSError' in act.end_event.raw_message


def test_action_dict_access():
    log = _get_logger()
    act = log.debug('test')
    act['key1'] = 'val1'
    assert act['key1'] == 'val1'
    act.success()


def test_action_non_trans_status_char():
    log = _get_logger()
    act = log.debug('test')
    act.success()  # non-trans (no __enter__)
    # status_char should be lowercase for non-trans
    assert act.end_event.status_char == 's'


def test_action_trans_status_char():
    log = _get_logger()
    with log.debug('test') as act:
        act.success()
    # status_char should be uppercase for trans
    assert act.end_event.status_char == 'S'