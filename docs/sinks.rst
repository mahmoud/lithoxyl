The Sink
========

In Lithoxyl's system of instrumentation, Records are used to carry
messages, data, and timing metadata through the Loggers to their
destination, the Sinks. This chapter focuses in on this last
step.

Writing a simple Sink
---------------------

Sinks can grow to be very involved, but a useful Sink can be as
simple as::

  import sys

  class DotSink(object):
      def on_end(self, end_event):
          sys.stdout.write('.')
          sys.stdout.flush()


Note that our new Sink does not have to inherit from any special
object. DotSink is a correct and capable Sink, ready to be
instantiated and installed with :meth:`Logger.add_sink`, just like in
:ref:`the overview <configuring_sinks>`. Once added to your Logger,
every time a Record ends, a dot will be written out to your console.

In this example, ``on_end`` is the handler for just one of Lithoxyl's
events. The next section takes a look at all five of them.

Events
------

Five events can happen in the Lithoxyl system:

* **begin** - The beginning of a Record, whether manually or through
  entering a context-managed block of code.

  The begin event corresponds to the method signature ``on_begin(self,
  begin_event)``. Designed to be called once per Record.
* **end** - The completion of a Record, whether manually
  (``success()`` and ``failure()``) or through exiting a
  context-managed block of code. There are three ways a Record can
  end, **success**, **failure**, and **exception**, but all of them
  result in an *end* event.

  The end event corresponds to the method signature ``on_end(self,
  end_event)``.  Designed to be called once per Record.
* **exception** - Called immediately when an exception is raised from
  within the context-managed block, or when an exception is manually
  handled with Record.exception(). Records ending in exception state
  typically fire two events, one for handling the exception, and one
  for ending the Record.

  The exception event corresponds to the Sink method signature
  ``on_exception(self, exc_event, exc_type, exc_obj, exc_tb)``.
  Designed to be called up to once.
* **warn** - The registration of a warning within a Record.

  Corresponds to the Sink method signature ``on_warn(self,
  warn_event)``. Can be called an arbitrary number of times.

* **comment** - The registration of a comment from a Logger. Comments
  are used for publishing metadata associated with a Logger.

  The comment event corresponds to the Sink method signature
  ``on_comment(self, comment_event)``. See here for more about
  comments.  Can be called an arbitrary number of times.

A Sink handles the event by implementing the respective method. The
event objects that accompany every event are meant to be practically
immutable; their values are set once, at creation.


.. Lithoxyl's informal Sink taxonomy ideas: numeric, accumulating,
   debug, stream.
