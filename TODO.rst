TODO
====

* Dynamic (as in scope) transaction association (parent ID)
* Parser from Formatter
* Emitters
* Filters for on_start/on_warn
* Integrate structured traceback stuff
* "auto" mode for escaping (eliminate excessive quoting)

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
