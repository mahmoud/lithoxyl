TODO
====

* Level remapping
* Dynamic (as in scope) transaction association (parent ID)
* Parser from Formatter
* "auto" mode for escaping (eliminate excessive quoting)
* default-on fixed header for formatter?
* Callpoint for transaction-completion call, too (status call)
* First-class datetime Formatter/FormatField support (type_func)

Formatting
----------

* Shorteners
  * Bytes shortening (strutils.bytes2human)
  * Numeric shortening (K, M, etc.)
  * Time shortening (h, m, s, ms, us)
  * Shortened string
  * reprlib

Sinks/emitters
--------------

* process + pipe/socket
* rotating file utility

Stats TODOs
-----------

* Moving/decaying average (for rates/load)
* calculate accumulated machine epsilon on some of the accumulators
* try out Decimal-based moment accumulator (to see how slow it is

helper: get_record_parent(record):

* Nonconcurrent: logger's last started transaction
* Greenlet: Greenlet local dict with stacks
* Threads: thread local dict with stacks
* Callbacks: Up 2 u


Ideal behavior: Only tell me about completing things unless there is
an inner task or the task is taking a long time (heartbeat-based
flush).


Linty things
------------

* Find all sinks that aren't installed in loggers


Header things
-------------

* Encoding
* File creation time
* Original hostname, file path
* Formatter string
