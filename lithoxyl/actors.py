
import os
import time
import threading

# TODO: what to do in systems without threading?
# TODO: signal actor for kicks?

DEFAULT_INTERVAL = 200  # milliseconds


class IntervalThreadActor(object):
    """Manages a thread that calls a *task* function and waits
    *interval* milliseconds before calling the function again.

    Failures and exceptions do not halt this loop.

    Args:
      task (callable): Function to call periodically. Takes no arguments.
      interval (number): Milliseconds to wait before next call of `process`.

    """
    def __init__(self, task, interval=DEFAULT_INTERVAL, **kwargs):
        self.task = task
        if not callable(task):
            raise ValueError('expected callable for task, not %r' % task)

        self._thread = None
        self._stopping = threading.Event()
        self._pid = None

        if interval is None:
            interval = DEFAULT_INTERVAL
        self.interval = self._orig_interval = float(interval)
        max_interval = kwargs.pop('max_interval', None)
        self.max_interval = float(max_interval or interval * 8)
        self._daemonize_thread = kwargs.pop('daemonize_thread', True)
        self._note = kwargs.pop('note', None)
        if self._note and not callable(self._note):
            raise ValueError('expected callable for note, not %r' % self._note)
        if kwargs:
            raise TypeError('unexpected keyword arguments: %r' % kwargs.keys())

        self._run_start_time = 0
        self._task_call_time = 0
        self._task_call_count = 0

    def get_stats(self):
        ret = {'run_start_time': self._run_start_time,
               'task_call_time': self._task_call_time,
               'task_call_count': self._task_call_count}
        return ret

    def is_alive(self):
        return self._thread and self._thread.is_alive()

    def start(self):
        if self.is_alive():
            return
        # os.getpid compare allows restarting after forks
        if os.getpid() == self._pid and self._stopping.is_set():
            # alive and stopping
            raise RuntimeError('expected caller to wait on join'
                               ' before calling start again')
        self._pid = os.getpid()
        self._stopping.clear()
        self._thread = threading.Thread(target=self._run)
        self._thread.daemon = self._daemonize_thread
        self._thread.start()
        return

    def stop(self):
        "actually, 'start_stopping' is more accurate"
        # TODO: what if we fork and the _run hasn't finished stopping,
        # so stopping is still set, but the thread is not alive. need
        # to reset the stopping state, or raise an error because the
        # data might not be clean.
        if self.is_alive():
            self._stopping.set()
        else:
            self._stopping.clear()
        return

    def join(self, timeout=None):
        if not self._thread:
            raise RuntimeError('actor must be started before it can be joined')
        self._thread.join(timeout=timeout)
        ret = self.is_alive()
        if not ret:
            self._stopping.clear()
        return ret

    def note(self, name, message, *a, **kw):
        if self._note:
            name = 'actor_' + str(name)
            self._note(name, message)
        return

    def _run(self):
        self._run_start_time = time.time()
        # TODO: start delay/jitter?
        try:
            while not self._stopping.is_set():
                self._task_call_count += 1
                cur_start_time = time.time()
                try:
                    self.task()
                except (SystemExit, KeyboardInterrupt):
                    if not self._daemonize_thread:
                        raise
                except Exception as e:
                    self.note('task_exception', '%s - task() (%r) raised: %r'
                              % (time.time(), self.task, e))
                    self.interval = min(self.interval * 2, self.max_interval)
                else:
                    decrement = (self.max_interval - self._orig_interval) / 8
                    self.interval = max(self.interval - decrement,
                                        self._orig_interval)
                cur_duration = time.time() - cur_start_time
                self._task_call_time += cur_duration
                interval_seconds = self.interval / 1000.0
                self._stopping.wait(interval_seconds)
        finally:
            self._stopping.clear()
        return
