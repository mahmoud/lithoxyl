

# import faulthandler
# faulthandler.enable()

import lithoxyl
from lithoxyl import (Logger,
                      StreamEmitter,
                      SensibleSink,
                      SensibleFilter,
                      SensibleFormatter as SF)


stderr_fmt = SF(begin='{status_char}+{import_delta_ms}ms - {begin_message}',
                end='{status_char}+{import_delta_ms}ms - {duration_ms}ms - {end_message}')


stderr_emt = StreamEmitter('stderr')
stderr_filter = SensibleFilter(success='info',
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

# context.get_context().enable_async()

log = Logger('test', sinks=[stderr_sink])


def one_two():
    with log.critical('first') as r1:
        r1['x'] = 'hi'
        with log.critical('second'):
            print('did some work')
        raise ValueError("oh no, one of those")
    return


for i in range(20):
    one_two()


import os
print(os.getpid())


class CommentSink(object):
    def on_comment(self, comment_event):
        print(comment_event, comment_event.message)
        # import pdb;pdb.set_trace()


def emit_cur_time_hook(logger):
    logger.comment('simpler heartbeats for a simpler time')


log.preflush_hooks.append(emit_cur_time_hook)
log.add_sink(CommentSink())

# log.flush()


log.comment('{} {hah}', 'hah!', hah='HAH!')

import pdb;pdb.set_trace()
