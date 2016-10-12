Notes
=====

Some implementation thoughts/reminders.

Sensibilities
-------------

One major area of contention is how to resolve the inherent
heterogeneity of expected and unexpected cases. Do we really want
exceptions being logged in the same place as non-exceptions? The
nature of the loggable data fundamentally changes. There are stack
traces for exceptions, for instance. Apache has access_log and
error_log by default, too.

Sinks
-----

* Both filtration and log verbosity are only provided at the sink
  level to prevent functionality from getting too diffuse. Built-in
  logging is intensely diffuse, with filtration, etc. at every level.

**"Classic" Handler-style Sink**::

  Sink(filterer, formatter, emitter)

* Allows for mixing and matching of pre-existing, sanely-defaulted
  components.
* Explicit and imperative: each component can/should be individually
  instantiated and configured.

Filterers are callables that take a Message object and return True or
False depending on whether the Sink should further handle a given
message. *Tentative:* Exceptions raised during filtration will result in
a message to ``stderr``, but are otherwise treated as False.

Using a subset of new-style Python format string syntax, Formatters
facilitate the creation of structured, but human-readable logs. By
extracting references out of format strings, Formatters can default
missing arguments, as well as effectively detect/correct/report
runtime formatting errors. Furthermore, by only providing values known
to be referenced by a format string, this argument extraction scheme
reduces formatting overhead and allow for an expanded set of
convenient formatting builtins, such as robust date formats.

Emitters take care of the actual serialization. A basic set of useful
emitters, including asynchronous and threadsafe implementations, is a
must.

Vocab angst
-----------

* Start: begin, open, init
* Stop: finish, end, complete, close, (commit?)

* Start, Stop, and Success all have the same first letter :(
* Solution: begin, end, success, failure, exception

Encoding woes
-------------

* If a stream has encoding set on it, does that mean it will
  automatically encode unicode objects passed to it?
* If so, should I be manually encoding that stuff for safety (in the
  emitter). Look at built-in logging (starting at line 834 of
  logging/__init__.py for what appears to be a faceplant of an impl)


* lithoxyl will only support python code written in the ASCII or UTF-8
  encodings.

Context manager laments
-----------------------

At one point, as a convenience, I wanted to make nested context
managers flat. For instance::

  def do_work(data):
      with logger.debug('saving file {path}', path=path) as log_rec:
          #
          # processing
          #
          with open(path, 'wb') as f:
              f.write(data)
      return

The double nesting of the with statements might not be too bad in this
example, but code gets pretty zigzaggy as they're put together. And
for larger blocks like thread locks, this can get pretty gnarly.

I was hoping to flatten it out into something like this::

  def do_write(data):
      with logger.debug_mgr('writing file {path}', open, path, 'wb') as rec, f:
          f.write(data)
      return

It seems simple enough, but it's not meant to be.

* Can't ``__enter__`` both at the same time. The Record has to be
  entered, then the function called, then a single result returned for
  entry.
* Can't return a tuple like in the fake example. Tuples aren't enterable
* Have to choose to return either the callable's return or the
  Record. The Record can hold the result, but not all results can hold
  the return.
* Because the ``__enter__`` has to be called manually, there's no
  guarantee of ``__exit__``. What happens to Records created by
  debug_mgr() that aren't entered.



Grasshopper mode
----------------

"When you can take the pebble from my hand, it will be time for you to leave"

I don't know about other people, but it hasn't been easy building up
the ego to be opinionated in infrastructure design. This difficulty
reaches a fever pitch with logging/lithoxyl, because one can't even
enforce opinions one _does_ have. It would be egregiously remiss to
raise an exception that interrupts the application's primary role in a
production environment, just to yell at a developer who may or may not
be in a position to understand the issue, learn about the problem, and
implement the fix. Then again, an infrastructure developer would be
remiss to altogether forsake teaching best practices through code.

Grasshopper mode is/will be a flag that increases verbosity to stderr,
for visibility into in various warning cases that definitely shouldn't
fail in production. Encoding issues, formatting failures, and minor
configuration yellow flags.

It differs from "training wheels" because it's not some sort of
magic/easy-mode switch that attempts to guess what developers
meant. It differs from linting because it's not static analysis
capable of running over whole codebases.


posix_fadvise
-------------

from ctypes import cdll, c_uint
libc = cdll.LoadLibrary('libc.so.6')
f = open('file.txt', 'w')
# fd, offset, len, advice_constant  (or is it len, offset)
libc.posix_fadvise(c_uint(f.fileno()), c_uint(0), c_uint(0), c_uint(3))


Misc.
-----

* known complexity of custom format fields: Logger and Sink both need to know about them since Logger formats the message and Sink formats the line
  * Lazy evaluation
  * Log-level filtration
  * Custom logger with log-level filtration
  * Rich taxonomy of Sinks (differentiate between numerical, textual, log levels and build a routing table up-front)
  * Ask Sinks whether they want a particular record for every record (no routing table)
  * Ask Sinks what fields they're interested in
  * Ask Sinks what fields they're interested in under what conditions (dictionary of field to condition)

  * lazily format the message <-

GUID stuff
----------

$ python -c "from lithoxyl.action import _ACT_ID_ITER; from lithoxyl.sensible import _get_id_guid; print _get_id_guid(next(_ACT_ID_ITER))"
a4c272b1cf8c
$ python -m timeit -s "from lithoxyl.action import _ACT_ID_ITER; from lithoxyl.sensible import _get_id_guid" "_get_id_guid(next(_ACT_ID_ITER))"
1000000 loops, best of 3: 0.904 usec per loop
$ python -m timeit -s "from lithoxyl.action import Action" "Action(None, 'critical', 'name', parent=object())"
100000 loops, best of 3: 3.15 usec per loop

A bit heavy to do for every single one, but probably good as a lazy/cached property.
