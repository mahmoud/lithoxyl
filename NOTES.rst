Notes
=====

Some implementation thoughts/reminders.

TODO
----

* handle_exc for X-Treme automated runtime debugging logs
* how to register additional levels
* removal of global level constants?
* default-on fixed header for formatter
* concurrency association IDs

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

Formatter built-ins
-------------------

* message_name
* logger_name
* status_name
* status_num  (_int? _code? _val?)
* level_name
* level_num  (built-in logging calls it levelno, parallel with lineno)
* func_name
* lineno
* module_name
* module_path
* lasti
* duration_secs
* duration_msecs
* start_time  (formats tbd, obvs)
* end_time

* (exception infos)
* (os infos? pid, etc.)
