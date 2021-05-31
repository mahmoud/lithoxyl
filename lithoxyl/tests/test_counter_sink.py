# -*- coding: utf-8 -*-

from __future__ import absolute_import
from lithoxyl import Logger
from lithoxyl.sinks import CounterSink


def test_basic_counter():
    csink = CounterSink()
    log = Logger('ctr_log', [csink])
    log.debug('t').success('est')

    assert csink.counter_map[log]['t'] == 1

    for i in range(1000):
        log.debug('e').success('st')

    assert csink.counter_map[log]['e'] == 1000
    assert csink.counter_map[log].get('t') == 0

    cdict = csink.to_dict()
    assert cdict == {'ctr_log': {'e': 1000,
                                 '__all__': 1001,
                                 '__missing__': 1}}
    return
