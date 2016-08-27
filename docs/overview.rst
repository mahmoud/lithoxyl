Lithoxyl Overview
=================

Lithoxyl is next-generation logging and instrumentation for
Python. This practical tutorial walks new users through the
fundamentals necessary to get up and running with Lithoxyl in under 10
minutes.

Motivating factors
------------------

Lithoxyl began as a response to the tired traditions of
logging. Traditions that included omission, procrastination, and only
adding it once things break.

Logging is not the last step anymore. Lithoxyl makes instrumentation
worthwhile from day 1, so all your projects are designed for
introspection. Lithoxyl achieves this by taking full advantage of
Python's rich syntax and runtime, providing features ranging from
metrics collection to structured logging to interactive debugging
hooks.

The Lithoxyl approach is practical. After running ``pip install
lithoxyl``, integrating Lithoxyl comes down to two steps:
instrumentation and configuration. First, instrumentation.

Instrumenting with Actions
--------------------------

With Lithoxyl, all instrumentation, including logging, starts with
knowing your application. We want to find the important parts of your
application and wrap them in microtransactions, called Actions.

Much more than print statements, Actions are lightweight objects that
track the state of code execution, from timing information to uncaught
exceptions. Each Action also has a name and a level, to enable
aggregation and filtering.

Actions are created with Loggers. We get into creating and configuring
Loggers later in the overview, but here's a basic example of creating
an *info*-level Action with a preconfigured Logger:

.. code-block:: python

  import backend           # some convenient backend logic for brevity
  from log import app_log  # preconfigured Lithoxyl Logger

  def create_entry(name):
      with app_log.info('adding entry by name'):
          name = name.strip()
          backend.add_by_name(name)
      return True

As you can see, the transactionality of Actions translates well to
Python's :term:`with` context manager syntax. A single line of logging
code succinctly records the beginning and ending of this code
block. Even better, there's no chance of missing an unexpected
exception. For instance, if **name** is not a string, and **.strip()**
raises an :exc:`AttributeError`, then that exception is guaranteed to
be captured and recorded.

You can do so much more with actions. Using dictionary syntax,
arbitrary data can be added to the action. And while actions finish
with a success status and autogenerate a message if no exception is
raised, failures and exceptions can also be set manually:

.. code-block:: python

  import backend
  from log import app_log

  def set_entry_state(name, state):

      with app_log.info('setting entry state') as act:
          act['name'] = name
          status = backend.STATE_MAP[state.lower()]
          success = backend.set_entry_state(name, state)
          if not success:
              act.failure('set {name} status to {state} failed', state=state)

       return success

As seen above, actions can also have a custom completion message,
which supports templating with new-style formatting syntax, using data
from within the action's data map (*name*), as well as arguments and
keyword arguments (*state*).

.. note::

   Even if message formatting fails, the log message will still be
   recorded. Only the failing segments will be left unformatted. As a
   rule, Lithoxyl degrades gracefully, to minimize impact to your
   application's primary functionality.

Furthermore, in cases like this, where you want the whole function
logged, you can use the logger's :meth:`~Logger.wrap` method.::

  import backend
  from log import app_log

  @app_log.wrap('critical', inject_as='act')
  def delete_entry(name, act):
      try:
          ret = backend.delete_entry_by_name(name.strip())
      except backend.EntryNotFound:
          # log soft error, let other exceptions raise through
          act.failure('no entry with name: {}', name)
          ret = False
      return ret

Note the decorator syntax, as well as the ability to inject the
action as one of the arguments of the function. This reduces the
instrumentation's code footprint even further.

That about covers creating and interacting with actions. Now we turn
to the origin and destination of the actions we create and populate:
Loggers and Sinks.

Creating Loggers
----------------

Actions make up most of an application's interaction with Lithoxyl,
but it would not be very easy to create an Action without a Logger.

As we learned above, before an Action can be populated, it must be
created, and Actions are created through Logger. As for the Logger
itself, here is how it is created::

  from lithoxyl import Logger

  app_log = Logger('entry_system')

Like that, the Logger we've been using above is ready to be
imported. A Logger is a lightweight, simple object, requiring only a
name. They are designed to be created once, configured, and imported
by other modules. That said, they are conceptually very useful.

Loggers generally correspond to parts or aspects of the
application. Small- to medium-sized applications can be fully
instrumented with just one Logger, but as applications grow, they tend
to add aspects. For example, if file access grows increasingly
important to an application, it would make sense to add a dedicated
low-level log just for instrumenting file access::

  file_log = Logger('file_access')

In short, Loggers themselves are simple, and designed to be fit to
your application, no matter how many aspects it may have. On their
own, they are conceptually useful, but without Sinks, they are all
potential.

.. _configuring_sinks:

Configuring Sinks
-----------------

So far, we have discovered two uses of the Lithoxyl Logger:

  * Creating actions
  * Segmenting and naming aspects of an application

Now, we are ready to add the third: publishing log events to the
appropriate handlers, called Sinks. Actions can carry all manner of
messages and measurements. That variety is only surpassed by the
Sinks, which handle aggregation and persistence, through log files,
network streams, and much more. Before getting into those
complexities, let's configure our ``app_log`` with a simple but very
useful sink::

  from lithoxyl import AggregateSink

  agg_sink = AggregateSink(limit=100)
  app_log.add_sink(agg_sink)

Now, by adding an instance of the AggregateSink to the ``app_log``, we
have a technically complete system. At any given point after this, the
last 100 events that passed through our application log will be
available inside ``agg_sink``. However, AggregateSinks only provide
in-memory storage, meaning data must be pulled out, either through a
monitoring thread or network service. Most developers expect
persistent logging to streams (stdout/stderr) and files. Lithoxyl is
more than capable.

Logging Sensibly
----------------

For developers who want a sensible and practical default Sink,
Lithoxyl provides the SensibleSink. The Sensible Suite chapter has a
full introduction, so let's just cover the basics.

The Sensible approach has 3 steps:

1. **Filter** - Optionally ignore events for a given Sink.
2. **Format** - Convert an event into a string.
3. **Emit** - Output the formatted string to a file, database, network, etc.

While totally pluggable and overridable, the Sensible suite ships with
types for each of these::

  from lithoxyl import (SensibleFilter,
                        SensibleFormatter,
                        StreamEmitter,
                        SensibleSink)

  # Create a filter that controls output verbosity
  fltr = SensibleFilter(success='critical',
                        failure='info',
                        exception='debug')

  # Create a simple formatter with just two bits of info:
  # The time since startup/import and end event message.
  # These are just two of the built-in "fields",
  # and the syntax is new-style string formatting syntax.
  fmtr = SensibleFormatter('+{import_delta_s} - {end_message}')

  # Create an emitter to write to stderr. 'stdout' and open file objects
  # also behave predictably.
  emtr = StreamEmitter('stderr')

  # Tie them all together. Note that filters accepts an iterable
  sink = SensibleSink(filters=[fltr], formatter=fmtr, emitter=emtr)

  # Add the sink to app_log, a vanilla Logger created above
  app_log.add_sink(sink)

In these six lines of code, using only built-in Lithoxyl types, we
create a filter, formatter, and emitter, then we bind them all
together with a SensibleSink. The output is first filtered by our
SensibleFilter, which only shows critical-level successes and
info-level failures, but shows all exceptions. Our SensibleFormatter
provides a simple but practical output, giving us a play-by-play
timing and message. That message is output to stderr by our
StreamEmitter. Just don't forget to add our newly-created SensibleSink
to the app_log.

As configured, the app_log will now write to stderr output that looks
like::

  +0.015255 - "load credential succeeded"
  +0.179199 - "client authorization succeeded"
  +0.344523 - "load configuration succeeded"
  +0.547119 - "optional backup failed"
  +1.258266 - "processing task succeeded"

Ain't it a thing of beauty? Here we see the SensibleFormatter at
work. It may not look like much, but there is a powerful feature at
work.

The ambitious aim underlying the Sensible approach is to create
human-readable structured logs. These are logs that are guaranteed to
be uniformly formatted and escaped, allowing them to be loaded for
further processing steps, such as collation with other logs, ETL into
database/OLAP, and calculation of system-wide statistics. Extending
the flow of logged information opens up many new roads in debugging,
optimization, and system robustification, easily justifying a bit of
extra up-front setup.

Here we only used two fields, *import_time_s* and *end_message*. The
list of Sensible built-in fields is quite expansive and worth a look
when designing your own log formats.
