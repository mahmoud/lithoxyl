The Action
==========

*Actions* are Lithoxyl's primary interface for instrumenting your
application. Actions are created with a
:class:`~lithoxyl.logger.Logger` instance, and are used to wrap
functions and code blocks.

At their most basic, Actions have a:

  * **name** - A string description of the behavior being wrapped.
  * **level** - An indicator of the importance of the action (debug, info, critical).
  * **status** - The state of the action (begin, success, failure, exception).
  * **duration** - The time between the begin and end events of a
    completed action, i.e., the time between entering and exiting a
    code block.

To track this information, Lithoxyl wraps important pieces of
your application in microtransactions called Actions::

  with log.info('user creation', username=name) as act:
      succeeded = _create_user(name)
      if not succeeded:
          act.failure()

This pattern is using an *info*-level Action as a *context manager*. The indented
part of the code after the :term:`with` statement is the code block
managed by the Action. Here is how the basics of the Action are
populated in our example:

  * **name** - "user creation"
  * **level** - INFO
  * **status** - *failure* if ``_create_user(name)`` returns a falsey
    value, *exception* if it raises an exception, otherwise defaults
    to *success*.
  * **duration** - Set automatically, duration is the time difference
     from before the execution of the first line of the code block to
     after the execution of the last line in the code block, or the
     ``r.failure()`` call, depending on the outcome of
     ``_create_user(name)``.

There's quite a bit going on, but Lithoxyl has several tricks that let
it flow with the semantics of applications. First, let's learn a bit
about these attributes, starting with the Action level.

.. automodule:: lithoxyl.action

.. _levels:

Action level
------------

Levels are a basic indicator of how important a block of application
logic is. Lithoxyl has three built-in levels. In order of increasing
importance:

* **debug** - Of interest to developers. Supplementary info for when
  something goes wrong.
* **info** - Informational. Can be helpful to know even when there are
  no problems.
* **critical** - Core functionality. Essential details at all times.

When instrumenting with Lithoxyl, the developer is always asking, how
significant is the success of this code block, how catastrophic is a
failure in this function?

It's only natural that instrumented code will start with more
*critical* actions. The most important parts should be instrumented
first. Eventually the instrumentation spreads to lower levels.

.. note::

   As a general tendency, as code gets closer to the operating system,
   the corresponding Action also gets a lower level. High-level
   operations get higher levels of Actions. Start high and move lower
   as necessary.

.. _status:

Action status
-------------

The Lithoxyl Action has an eventful lifetime. Even the most basic
usage sees the Action going from creation to beginning to one of the
ending states: success, failure, or exception.

First, simply creating an Action does not "begin" it. An action begins
when it is entered with a **with** statement, as we saw in the example
above. Entering an action creates a timestamp and makes it the parent
of future actions, until it is ended.

There are three end statuses:

* **success** - The action described by the action completed without
  issue. This is the automatic default when no exception is raised.
* **failure** - The action did not complete successfully, and the
  failure was expected and/or handled within the application.
* **exception** - The action terminated unexpectedly, likely with a
  Python exception. This is the automatic default when an exception is
  raised within an action context manager.

The split between *failure* and *exception* should be familiar to
users of standard testing frameworks like `py.test`_. Test frameworks
distinguish between a test that fails and a test that could not be
fully run because the test code raised an unexpected
exception. Lithoxyl brings these semantics into an application's
runtime instrumentation.

.. _py.test: http://pytest.org

.. note::

   If an action is manually set to complete with
   :meth:`~Action.success()` or :meth:`~Action.failure()`, and an
   unexpected exception occurs, the Action will end with the
   *exception* status.

Action API
----------

Actions are usually constructed through Loggers, but it can help to
know the underlying API and see the obvious parallels.

.. autoclass:: lithoxyl.action.Action
   :members:


.. _concurrency:

Action concurrency
------------------

TODO
