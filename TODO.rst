TODO
====

* Make wrap use boltons
* DummyRecord
* Level remapping
* Dynamic (as in scope) transaction association (parent ID)
* Parser from Formatter
* Callpoint for transaction-completion call, too (status call)
* First-class datetime Formatter/FormatField support (type_func)
* Back-propagation of events like log file rotation, if in fact that
  should be encapsulated in lower-level objects like Emitters.
* Should .comment() have an "immediate" mode where they acquire the
  flush lock and do not go into the async queue?

Formatting
----------

* Shorteners
  * Bytes shortening (strutils.bytes2human)
  * Numeric shortening (K, M, etc.)
  * Time shortening (h, m, s, ms, us)
  * Shortened string
  * reprlib
* cur_event timestamps

Sinks/emitters
--------------

* process + pipe/socket
* rotating file utility

Stats TODOs
-----------

* calculate accumulated machine epsilon on some of the accumulators
* try out Decimal-based moment accumulator (to see how slow it is)

Concurrency
-----------

* Greenlet: Greenlet local dict with stacks
* Threads: thread local dict with stacks
* Callbacks: Up 2 u


Ideal behavior: Only tell me about completing things unless there is
an inner task or the task is taking a long time (heartbeat-based
flush).

General formatter advice: Put shorter, fixed-width items closer to the
start of the line, put longer, more dynamic items toward the end of
the line.


Linty things
------------

* Find all sinks that aren't installed in loggers
* Higher-importance records nested within lower importance records
  (e.g., critical coming from within debug)

Header things
-------------

* Encoding
* File creation time
* Original hostname, file path
* Formatter string
