# -*- coding: utf-8 -*-

import syslog

from lithoxyl.common import DEBUG, INFO, CRITICAL, get_level


class SyslogEmitter(object):

    default_priority_map = {DEBUG: {'success': syslog.LOG_DEBUG,
                                    'failure': syslog.LOG_INFO,
                                    'warn': syslog.LOG_INFO,
                                    'exception': syslog.LOG_NOTICE},
                            INFO: {'success': syslog.LOG_INFO,
                                   'failure': syslog.LOG_NOTICE,
                                   'warn': syslog.LOG_NOTICE,
                                   'exception': syslog.LOG_WARNING},
                            CRITICAL: {'success': syslog.LOG_NOTICE,
                                       'failure': syslog.LOG_WARNING,
                                       'warn': syslog.LOG_WARNING,
                                       'exception': syslog.LOG_ERR}}

    def __init__(self, ident, priority_map=None,
                 options=syslog.LOG_PID, facility=syslog.LOG_USER):
        self.ident = ident
        self.options = options
        self.facility = facility

        # TODO merge and resolve
        self.priority_map = priority_map or self.default_priority_map

        self.syslog_conn = syslog.openlog(ident, options, facility)

    def _get_syslog_priority(self, event_name, action):
        level = get_level(action.level)

        if event_name == 'warn':
            status = 'warn'
        elif event_name == 'begin':
            status = 'begin'
        else:
            status = action.status
        return self.priority_map[level][status]

    def on_begin(self, begin_event, entry):
        priority = self._get_syslog_priority('begin', begin_event)
        syslog.syslog(priority, entry)

    def on_warn(self, warn_event, entry):
        priority = self._get_syslog_priority('warn', warn_event)
        syslog.syslog(priority, entry)

    def on_end(self, end_event, entry):
        priority = self._get_syslog_priority('end', end_event)
        syslog.syslog(priority, entry)
