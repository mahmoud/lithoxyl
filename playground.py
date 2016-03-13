

# import faulthandler
# faulthandler.enable()

from lithoxyl import (Logger,
                      SensibleSink,
                      ThresholdFilter,
                      StreamEmitter,
                      Formatter)

stderr_fmt = Formatter(begin='{status_char}{begin_local_iso8601_noms_notz} - {begin_message}',
                       complete='{status_char}{end_local_iso8601_noms_notz} - {duration_msecs}ms - {end_message}')


stderr_fmt = Formatter(begin='{status_char}+{import_delta_ms}ms - {begin_message}',
                       complete='{status_char}+{import_delta_ms}ms - {duration_msecs}ms - {end_message}')


stderr_emt = StreamEmitter('stderr')
stderr_filter = ThresholdFilter(success='info',
                                failure='debug',
                                exception='debug',
                                begin='debug')
stderr_sink = SensibleSink(formatter=stderr_fmt,
                           emitter=stderr_emt,
                           filters=[stderr_filter])


#ff = FancyFilter(success='info',
#                 failure='debug',
#                 exception='debug',
#                 begin='debug',
#                 with_begin=True)

from lithoxyl import context

#context.get_context().enable_async()

log = Logger('test', sinks=[stderr_sink])

with log.critical('first') as lr1:
    with log.critical('second') as lr2:
        print 'did some work'

import os
print os.getpid()


class CommentSink(object):
    def on_comment(self, comment_event):
        print comment_event, comment_event.message
        # import pdb;pdb.set_trace()


def emit_cur_time_hook(logger):
    logger.comment('simpler heartbeats for a simpler time')


log.preflush_hooks.append(emit_cur_time_hook)
log.add_sink(CommentSink())

# log.flush()


log.comment('{} {hah}', 'hah!', hah='HAH!')

import pdb;pdb.set_trace()
