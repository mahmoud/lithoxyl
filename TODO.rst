TODO
====

* Dynamic (as in scope) transaction association (parent ID)
* Parser from Formatter
* "auto" mode for escaping (eliminate excessive quoting)
* register additional levels? remove global level constants?
* default-on fixed header for formatter?
* Callpoint for transaction-completion call, too (status call)
* autoincremented IDs for loggers and records?
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

* threaded
* process + pipe/socket
* syslog

* rotating file utility

Stats TODOs
-----------

* Moving/decaying average (for rates/load)
* calculate accumulated machine epsilon on some of the accumulators
* try out Decimal-based moment accumulator (to see how slow it is
