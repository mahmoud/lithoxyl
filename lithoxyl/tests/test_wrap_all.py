
import json
from xml.etree import ElementTree

from lithoxyl import Logger, AggregateSink
from lithoxyl.utils import wrap_all, unwrap_all


def test_wrap_all_json():
    agg_sink = AggregateSink()
    log = Logger('wrapper_log', sinks=[agg_sink])

    wrap_all(log, 'info', json)

    json.loads('{}')

    assert agg_sink.begin_events[0].name == 'json.loads'

    unwrap_all(json)

    json.loads('{}')

    assert len(agg_sink.begin_events) == 3

    return


def test_wrap_all_element_tree():
	log = Logger('test', sinks=[])

	# test old-style class wrapping / unwrapping
	wrap_all(log, target=ElementTree)
	unwrap_all(ElementTree)

