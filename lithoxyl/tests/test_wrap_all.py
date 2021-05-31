
from __future__ import absolute_import
import sys
import json
from xml.etree import ElementTree

import pytest

from lithoxyl import Logger, AggregateSink
from lithoxyl.utils import wrap_all, unwrap_all

IS_PY3 = sys.version_info[0] == 3
IS_PYPY = '__pypy__' in sys.builtin_module_names


def test_wrap_all_json():
    agg_sink = AggregateSink()
    log = Logger('wrapper_log', sinks=[agg_sink])

    wrap_all(log, 'info', json, skip_exc=True)

    json.loads('{}')

    assert agg_sink.begin_events[0].name == 'json.loads'

    unwrap_all(json)

    json.loads('{}')

    if IS_PYPY:
        # different impl
        assert len(agg_sink.begin_events) == 1
    else:
        assert len(agg_sink.begin_events) == 3

    return


@pytest.mark.skipif(IS_PY3, reason='no old-style classes and elementree is a builtin type/cannot setattr on it')
def test_wrap_all_element_tree():
    log = Logger('test', sinks=[])

    # test old-style class wrapping / unwrapping
    wrap_all(log, target=ElementTree)
    unwrap_all(ElementTree)
