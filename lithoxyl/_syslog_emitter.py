# -*- coding: utf-8 -*-

import syslog

from common import DEBUG, INFO, CRITICAL, get_level


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

    def _get_syslog_priority(self, event_name, record):
        level = get_level(record.level)

        if event_name == 'warn':
            status = 'warn'
        elif event_name == 'begin':
            status = 'begin'
        else:
            status = record.status
        return self.priority_map[level][status]

    def on_begin(self, begin_record, entry):
        priority = self._get_syslog_priority('begin', begin_record)
        syslog.syslog(priority, entry)

    def on_warn(self, warn_record, entry):
        priority = self._get_syslog_priority('warn', warn_record)
        syslog.syslog(priority, entry)

    def on_complete(self, complete_record, entry):
        priority = self._get_syslog_priority('complete', complete_record)
        syslog.syslog(priority, entry)
