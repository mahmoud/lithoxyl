Notes
=====

Some implementation thoughts/reminders.

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
