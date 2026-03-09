import sys
import types
import pytest
from unittest.mock import patch, MagicMock

# Ensure syslog module exists (may be absent on non-Unix)
if 'syslog' not in sys.modules:
    mock_syslog_module = types.ModuleType('syslog')
    mock_syslog_module.LOG_DEBUG = 7
    mock_syslog_module.LOG_INFO = 6
    mock_syslog_module.LOG_NOTICE = 5
    mock_syslog_module.LOG_WARNING = 4
    mock_syslog_module.LOG_ERR = 3
    mock_syslog_module.LOG_PID = 0x01
    mock_syslog_module.LOG_USER = 8
    mock_syslog_module.openlog = MagicMock()
    mock_syslog_module.syslog = MagicMock()
    sys.modules['syslog'] = mock_syslog_module

import syslog
from lithoxyl._syslog_emitter import SyslogEmitter
from lithoxyl.common import DEBUG, INFO, CRITICAL


class MockAction:
    def __init__(self, level, status='success'):
        self.level = level
        self.status = status


class MockEvent:
    def __init__(self, level, status='success'):
        self.action = MockAction(level, status)
        self.level = level
        self.status = status


@patch('lithoxyl._syslog_emitter.syslog')
def test_construct(mock_sl):
    mock_sl.LOG_PID = syslog.LOG_PID
    mock_sl.LOG_USER = syslog.LOG_USER
    mock_sl.LOG_DEBUG = syslog.LOG_DEBUG
    mock_sl.LOG_INFO = syslog.LOG_INFO
    mock_sl.LOG_NOTICE = syslog.LOG_NOTICE
    mock_sl.LOG_WARNING = syslog.LOG_WARNING
    mock_sl.LOG_ERR = syslog.LOG_ERR
    emitter = SyslogEmitter('test_app')
    assert emitter.ident == 'test_app'
    mock_sl.openlog.assert_called_once_with('test_app', syslog.LOG_PID, syslog.LOG_USER)


def _make_emitter(mock_sl):
    """Configure mock syslog constants and return a fresh SyslogEmitter."""
    mock_sl.LOG_PID = syslog.LOG_PID
    mock_sl.LOG_USER = syslog.LOG_USER
    mock_sl.LOG_DEBUG = syslog.LOG_DEBUG
    mock_sl.LOG_INFO = syslog.LOG_INFO
    mock_sl.LOG_NOTICE = syslog.LOG_NOTICE
    mock_sl.LOG_WARNING = syslog.LOG_WARNING
    mock_sl.LOG_ERR = syslog.LOG_ERR
    return SyslogEmitter('test_app')


@patch('lithoxyl._syslog_emitter.syslog')
def test_on_begin_debug(mock_sl):
    emitter = _make_emitter(mock_sl)
    mock_sl.syslog.reset_mock()
    emitter.on_begin(MockEvent(DEBUG), 'starting task')
    mock_sl.syslog.assert_called_once_with(syslog.LOG_DEBUG, 'starting task')


@patch('lithoxyl._syslog_emitter.syslog')
def test_on_begin_info(mock_sl):
    emitter = _make_emitter(mock_sl)
    mock_sl.syslog.reset_mock()
    emitter.on_begin(MockEvent(INFO), 'starting task')
    mock_sl.syslog.assert_called_once_with(syslog.LOG_INFO, 'starting task')


@patch('lithoxyl._syslog_emitter.syslog')
def test_on_warn_debug(mock_sl):
    emitter = _make_emitter(mock_sl)
    mock_sl.syslog.reset_mock()
    emitter.on_warn(MockEvent(DEBUG), 'warning message')
    mock_sl.syslog.assert_called_once_with(syslog.LOG_INFO, 'warning message')


@patch('lithoxyl._syslog_emitter.syslog')
def test_on_end_success(mock_sl):
    emitter = _make_emitter(mock_sl)
    mock_sl.syslog.reset_mock()
    emitter.on_end(MockEvent(INFO, status='success'), 'task done')
    mock_sl.syslog.assert_called_once_with(syslog.LOG_INFO, 'task done')


@patch('lithoxyl._syslog_emitter.syslog')
def test_on_end_failure(mock_sl):
    emitter = _make_emitter(mock_sl)
    mock_sl.syslog.reset_mock()
    emitter.on_end(MockEvent(INFO, status='failure'), 'task failed')
    mock_sl.syslog.assert_called_once_with(syslog.LOG_NOTICE, 'task failed')


@patch('lithoxyl._syslog_emitter.syslog')
def test_on_end_exception(mock_sl):
    emitter = _make_emitter(mock_sl)
    mock_sl.syslog.reset_mock()
    emitter.on_end(MockEvent(CRITICAL, status='exception'), 'task exploded')
    mock_sl.syslog.assert_called_once_with(syslog.LOG_ERR, 'task exploded')


@patch('lithoxyl._syslog_emitter.syslog')
def test_custom_priority_map(mock_sl):
    mock_sl.LOG_PID = syslog.LOG_PID
    mock_sl.LOG_USER = syslog.LOG_USER
    mock_sl.LOG_ERR = syslog.LOG_ERR
    custom_map = {
        DEBUG: {'begin': syslog.LOG_ERR, 'success': syslog.LOG_ERR,
                'failure': syslog.LOG_ERR, 'warn': syslog.LOG_ERR,
                'exception': syslog.LOG_ERR},
        INFO: {'begin': syslog.LOG_ERR, 'success': syslog.LOG_ERR,
               'failure': syslog.LOG_ERR, 'warn': syslog.LOG_ERR,
               'exception': syslog.LOG_ERR},
        CRITICAL: {'begin': syslog.LOG_ERR, 'success': syslog.LOG_ERR,
                   'failure': syslog.LOG_ERR, 'warn': syslog.LOG_ERR,
                   'exception': syslog.LOG_ERR},
    }
    emitter = SyslogEmitter('test_app', priority_map=custom_map)
    mock_sl.syslog.reset_mock()
    emitter.on_begin(MockEvent(DEBUG), 'msg')
    mock_sl.syslog.assert_called_once_with(syslog.LOG_ERR, 'msg')
