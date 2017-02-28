The Sensible Suite
==================

Structured logging creates logs with a consistent format, allowing
them to be loaded later for further processing and analysis.

One of Lithoxyl's primary uses is as a toolkit for creating these
structured logs. The Sensible Suite is the first generalized approach
to offer structured logging without sacrificing human readability.

Let's look at an example. Perhaps the most common structured log is
the HTTP server access log, such as the one created by Apache or
nginx. A couple entries from that log might look like::

    78.178.243.200 - - [22/Jun/2013:15:02:31 -0700] "GET /favicon.ico HTTP/1.1" 404 570 "-" "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.116 Safari/537.36" "-"
    119.63.193.132 - - [22/Jun/2013:14:19:36 -0700] "GET / HTTP/1.1" 200 9755 "-" "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0)" "-"

It's a bit on the wide side, but here we see:

  * The `IP`_ of the client
  * The local date and time the request was received
  * The request line, including the method, path, and version
  * The response code returned to the client
  * The size of the response in bytes
  * The user agent from the client browser

.. _`IP`: https://en.wikipedia.org/wiki/IP_address

With the Sensible suite, each of these values becomes a *field*,
represented by SensibleField objects. The Sensible suite comes with
over twenty built-in fields to cover most use cases, and sensible
default handling for other values. These fields are used to create a
template for the SensibleFormatter, which knows how to turn a Lithoxyl
Action into a structured string. Let's see how it all comes together
by creating an equivalent log that uses Lithoxyl built-in behavior::

  from lithoxyl import SensibleFormatter, FileEmitter, Logger

  a_log = Logger('access_log')

  a_fmtr = SensibleFormatter('{ip} - [{iso_begin_local}] {req_line} {resp_code} {resp_len} {user_agent}')

  a_sink = SensibleSink(formatter=fmtr, emitter=FileEmitter('access.log'))

  a_log.add_sink(a_sink)

No arcane configuration format here. Everything is configured through
explicit Python code. The ``a_log`` logger has only one sink right
now, a SensibleSink that ties together three entities, in their
running order:

  * **Filters** - This list of objects checks each event, and returns
    True/False depending on whether it should be logged. See the
    :class:`~sensible.SensibleFilter` for more info.
  * **Formatter** - Turns events that make it through the filters into
    strings. The :class:`~sensible.SensibleFormatter` is the canonical
    formatter of the suite, though you're free to provide your own.
  * **Emitters** - Writes formatted strings into files or network
    streams. Emitters are not strictly a Sensible construct; several
    can be found in the :mod:`emitters` module.

The flow through the SensibleSink is clear: Filtration →  Formatting →
Output. Any actions passing through the ``a_log`` Logger will have
their *end* events logged to *access.log*.

The Sensible Interfaces
-----------------------

To achieve human-readable strutured logging, Lithoxyl's Sensible suite
uses four key types with a sensible naming scheme:

  * The :class:`~sensible.SensibleSink`
  * The :class:`~sensible.SensibleFilter`
  * The :class:`~sensible.SensibleFormatter`
  * The :class:`~sensible.SensibleField`

The first three are used fairly regularly, but SensibleField is mostly
behind the scenes. That said, the built-in fields can in many ways the
most important part. See the :ref:`Sensible Fields` section below for
details on those.

.. autoclass:: sensible.SensibleSink
.. autoclass:: sensible.SensibleFilter
.. autoclass:: sensible.SensibleFormatter


.. _fields:

Sensible Fields
---------------

There are many built-in Sensible Fields, for a variety of use
cases. First, some example code to set the context for the field examples::

    logger = Logger('test_logger')
    with logger.critical('test_task', reraise=False) as act:
        time.sleep(0.7)
        act['item'] = 'cur_item'
        act.failure('task status: {status_str}')
        raise ValueError('unexpected value for {item}')
    return act

And now the fields themselves:

    +-----------------------+----------------------------------------------------------------+-----------------------------------------------+
    | Name                  | Description                                                    | Example                                       |
    +=======================+================================================================+===============================================+
    | **logger_name**       | The name of the Logger, as set in the constructor. Quoted.     | ``"test_logger"``                             |
    +-----------------------+----------------------------------------------------------------+-----------------------------------------------+
    | **logger_id**         | An automatic integer ID. See :ref:`concurrency`.               | ``3``                                         |
    +-----------------------+----------------------------------------------------------------+-----------------------------------------------+
    | **action_name**       | Short string description of the action. Quoted.                | ``"test_task"``                               |
    +-----------------------+----------------------------------------------------------------+-----------------------------------------------+
    | **action_id**         | An automatic integer ID. See :ref:`concurrency`.               |  ``17``                                       |
    +-----------------------+----------------------------------------------------------------+-----------------------------------------------+
    | **action_guid**       | A globally unique ID string. See :ref:`concurrency`.           |  ``c3124107db02ff33dbde8e85``                 |
    +-----------------------+----------------------------------------------------------------+-----------------------------------------------+
    | **status_str**        | The full name of action status. See :ref:`status`.             | ``exception``                                 |
    +-----------------------+----------------------------------------------------------------+-----------------------------------------------+
    | **status_char**       | A single-character action status. See :ref:`status`.           | ``E``                                         |
    +-----------------------+----------------------------------------------------------------+-----------------------------------------------+
    | **level_name**        | Full name of the action level.                                 | ``critical``                                  |
    +-----------------------+----------------------------------------------------------------+-----------------------------------------------+
    | **level_name_upper**  | Full name of the action level, in uppercase. See :ref:`levels`.| ``CRITICAL``                                  |
    +-----------------------+----------------------------------------------------------------+-----------------------------------------------+
    | **level_char**        | Single-character form of the action level.                     | ``C``                                         |
    +-----------------------+----------------------------------------------------------------+-----------------------------------------------+
    | **level_number**      | The integer value associated with the action level.            | ``90``                                        |
    +-----------------------+----------------------------------------------------------------+-----------------------------------------------+
    | **data_map**          | JSON-serialized form of all values in the Action data map.     | ``{"item": "cur_item"}``                      |
    +-----------------------+----------------------------------------------------------------+-----------------------------------------------+
    | **data_map_repr**     | repr()-serialized form of all values in the Action data map.   | ``{"item": "cur_item"}``                      |
    +-----------------------+----------------------------------------------------------------+-----------------------------------------------+
    | **begin_message**     | The message associated with the event's action's begin event.  | ``"test_task beginning"``                     |
    +-----------------------+----------------------------------------------------------------+-----------------------------------------------+
    | **begin_message_raw** | Same as **begin_message**, before formatting.                  | ``"test_task beginning"``                     |
    +-----------------------+----------------------------------------------------------------+-----------------------------------------------+
    | **end_message**       | The message associated with the event's action's end event.    | ``"test_task raised ... ue for cur_item',)"`` |
    +-----------------------+----------------------------------------------------------------+-----------------------------------------------+
    | **end_message_raw**   | Same as **end_message**, before formatting.                    | ``"test_task raised ... lue for {item}',)"``  |
    +-----------------------+----------------------------------------------------------------+-----------------------------------------------+
    | **event_message**     | The message associated with the event.                         | ``"test_task raised ... ue for cur_item',)"`` |
    +-----------------------+----------------------------------------------------------------+-----------------------------------------------+
    | **event_message_raw** | Same as **event_message**, before formatting.                  | ``"test_task raised ... lue for {item}',)"``  |
    +-----------------------+----------------------------------------------------------------+-----------------------------------------------+
    | **duration_s**        | Duration in floating point number of seconds.                  | ``0.701``                                     |
    +-----------------------+----------------------------------------------------------------+-----------------------------------------------+
    | **duration_ms**       | Duration in floating point number of milliseconds (ms).        | ``700.908``                                   |
    +-----------------------+----------------------------------------------------------------+-----------------------------------------------+
    | **duration_us**       | Duration in floating point number of microseconds (us).        | ``700907.946``                                |
    +-----------------------+----------------------------------------------------------------+-----------------------------------------------+
    | **duration_auto**     | Duration in floating point with automatic unit (s/ms/us).      | ``700.908ms``                                 |
    +-----------------------+----------------------------------------------------------------+-----------------------------------------------+
    | **module_name**       | The name of the module where the action was created.           | ``"__main__"``                                |
    +-----------------------+----------------------------------------------------------------+-----------------------------------------------+
    | **module_path**       | The path of the module where the action was created.           | ``"misc/gen_field_table.py"``                 |
    +-----------------------+----------------------------------------------------------------+-----------------------------------------------+
    | **func_name**         | The name of the function that created the action               | ``get_test_action``                           |
    +-----------------------+----------------------------------------------------------------+-----------------------------------------------+
    | **line_number**       | The line number where the action was created.                  | ``26``                                        |
    +-----------------------+----------------------------------------------------------------+-----------------------------------------------+
    | **exc_type**          | The name of the exception type, if an exception was caught.    | ``ValueError``                                |
    +-----------------------+----------------------------------------------------------------+-----------------------------------------------+
    | **exc_message**       | The exception message, if there was one. Quoted.               | ``"unexpected value for {item}"``             |
    +-----------------------+----------------------------------------------------------------+-----------------------------------------------+
    | **exc_tb_str**        | The exception's full traceback, if there was one. Quoted.      | ``"Traceback (most r ... ue for {item}')\n"`` |
    +-----------------------+----------------------------------------------------------------+-----------------------------------------------+
    | **exc_tb_list**       | A JSON representation of the exception traceback. Quoted.      | ``"[Callpoint('get_t ... for {item}')\")]"``  |
    +-----------------------+----------------------------------------------------------------+-----------------------------------------------+
    | **process_id**        | The integer process ID. See :func:`os.getpid`.                 | ``19828``                                     |
    +-----------------------+----------------------------------------------------------------+-----------------------------------------------+

There can be some subtle nuances when designing your log
structure. For instance, when choosing which message to use for an
event, you almost certainly want **event_message**, which works
equally well with all event types, including begin, end, comment, and
warn.

Timestamp fields
~~~~~~~~~~~~~~~~

Timestamps are so important to logging, especially structured logging,
that they get a table of their own:

    +-------------------------------+----------------------------------------------------------------+-------------------------------------+
    | Name                          | Description                                                    | Example                             |
    +===============================+================================================================+=====================================+
    | **iso_begin**                 | The full ISO8601 begin event UTC timestamp, with timezone.     | ``2016-05-22T10:41:06.470354+0000`` |
    +-------------------------------+----------------------------------------------------------------+-------------------------------------+
    | **iso_end**                   | The full ISO8601 end event UTC timestamp, with timezone.       | ``2016-05-22T10:41:07.171262+0000`` |
    +-------------------------------+----------------------------------------------------------------+-------------------------------------+
    | **iso_begin_notz**            | The begin event ISO UTC timestamp, without timezone.           | ``2016-05-22T10:41:06.470354``      |
    +-------------------------------+----------------------------------------------------------------+-------------------------------------+
    | **iso_end_notz**              | The end event ISO UTC timestamp, without timezone.             | ``2016-05-22T10:41:07.171262``      |
    +-------------------------------+----------------------------------------------------------------+-------------------------------------+
    | **iso_begin_local**           | The begin event ISO local timestamp, with timezone.            | ``2016-05-22T03:41:06.470354-0700`` |
    +-------------------------------+----------------------------------------------------------------+-------------------------------------+
    | **iso_end_local**             | The end event ISO local timestamp, with timezone.              | ``2016-05-22T03:41:07.171262-0700`` |
    +-------------------------------+----------------------------------------------------------------+-------------------------------------+
    | **iso_begin_local_notz**      | The begin event ISO local timestamp, without timezone.         | ``2016-05-22T03:41:06.470354``      |
    +-------------------------------+----------------------------------------------------------------+-------------------------------------+
    | **iso_end_local_notz**        | The end event ISO local timestamp, without timezone.           | ``2016-05-22T03:41:07.171262``      |
    +-------------------------------+----------------------------------------------------------------+-------------------------------------+
    | **iso_begin_local_noms**      | The begin event ISO local timestamp, without subsecond timing. | ``2016-05-22T03:41:06 PDT``         |
    +-------------------------------+----------------------------------------------------------------+-------------------------------------+
    | **iso_end_local_noms**        | The end event ISO local timestamp, without subsecond timing.   | ``2016-05-22T03:41:07 PDT``         |
    +-------------------------------+----------------------------------------------------------------+-------------------------------------+
    | **iso_begin_local_noms_notz** | The begin event local times, without subsecond or timezone.    | ``2016-05-22T03:41:06``             |
    +-------------------------------+----------------------------------------------------------------+-------------------------------------+
    | **iso_end_local_noms_notz**   | The end event local times, without subsecond or timezone.      | ``2016-05-22T03:41:07``             |
    +-------------------------------+----------------------------------------------------------------+-------------------------------------+


The timestamp fields above are geared toward long-running processes
like servers. For shorter running processes, it's often more readable
and more useful to know the time between the log message and process
start.

    +-------------------------------+----------------------------------------------------------------+-------------------------------------+
    | Name                          | Description                                                    | Example                             |
    +===============================+================================================================+=====================================+
    | **import_delta_s**            | Floating-point number of seconds since lithoxyl import.        | ``2.887265``                        |
    +-------------------------------+----------------------------------------------------------------+-------------------------------------+
    | **import_delta_ms**           | Floating-point number of milliseconds since lithoxyl import.   | ``2887.265``                        |
    +-------------------------------+----------------------------------------------------------------+-------------------------------------+

Creating custom fields
~~~~~~~~~~~~~~~~~~~~~~

Most custom data does not require new fields. Unrecognized fields are
treated as quoted and escaped string data. If you want to change that
representation, you can create a SensibleField and either register it
locally with a Formatter, or globally, using
sensible.register_field().

.. autoclass:: sensible.SensibleField
