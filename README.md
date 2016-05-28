# lithoxyl

Application instrumentation and logging, with a geological
bent. Documentation is available on
[Read the Docs](http://lithoxyl.readthedocs.io).

## An infomercial of sorts

"Has this ever happened to you?"

Here's an example of some ostensibly well-instrumented code.

```python
import logging

def create_user(name):
    logging.info('creating user with name %r', name)
    try:
        success = _create_user(name)
        if success:
            logging.info('successfully created user %r', name)
        else:
            logging.error('failed to create user %r', name)
    except Exception:
        logging.critical('exception encountered while creating user %r',
                         name, exc_info=True)
    return success
```

Notice how the logging statements tend to dominate the code, almost
drowning out the meaning of the code.

Here's lithoxyl's take:

```python
from lithoxyl import stderr_log

def create_user(name):
    with stderr_log.critical('user creation', username=name, reraise=False) as r:
        success = _create_user(name)
        if not success:
            r.failure()
    return success
```


## Feature brief

* Transactional logging
* Semantic instrumentation
* Pure Python
* Pythonic context manager API minimizes developer errors
* Decorator syntax is convenient and unobtrusive
* Human-readable structured logs
* Reparseability thanks to autoescaping
* Statistical accumulators for prerolled metrics
* Programmatic configuration with sensible defaults just an import away
* Synchronous mode for simplicity
* Asynchronous operation for performance critical applications
* Log file headers for metadata handling
* Heartbeat for periodic output and checkpointing
* Automatic, fast log parser generation (TBI)
* Sinks
    * EWMASink
    * DebuggerSink
    * MomentSink
    * QuantileSink
    * StreamSink
    * SyslogSink
    * and more

## Reasons to use Lithoxyl

* More specific: distinguishes between level and status
* Safer: Transactional logging ensures that exceptions are always recorded appropriately
* Lower overhead: Lithoxyl can be used more places in code (e.g., tight loops), as well as more environments, without concern of excess overhead.
* More Pythonic: Python's logging module is a port of log4j, and it shows.
* No global state: Lithoxyl has virtually no internal global state, meaning fewer gotchas overall
* Higher concurrency: less global state and less overhead mean fewer places where contention can occur
* More succinct: Rather than try/except/finally, use a simple with block
* More useful: Lithoxyl represents a balance between logging and profiling
* More composable: Get exactly what you want by recombining new and provided components
* More lightweight: Simplicity, composability, and practicality, make Lithoxyl something one might reach for earlier in the development process. Logging shouldn't be an afterthought, nor should it be a big investment that weighs down development, maintenance, and refactoring.
