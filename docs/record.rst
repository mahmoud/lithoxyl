The Record
==========

Record objects are Lithoxyl's fundamental construct for instrumenting
application logic. Records are created with a
:class:`~lithoxyl.logger.Logger`, and wrap functions and code blocks
to collect messages and timing information.

Lithoxyl Records are like transactions wrapping important pieces of
your application::

  with log.info('user creation', username=name) as r:
      success = _create_user(name)
      if not success:
          r.failure()

At their most basic, Records have a:

  * **name** - A string description of the application action.
  * **level** - An indicator of the importance of the application action.
  * **status** - The state of the record (begin, success, failure, exception).
  * **duration** - The time between the begin and end events of a
    completed record, i.e., the time between entering and exiting the
    code block.

Read on to learn more about each of these attributes.

.. automodule:: lithoxyl.record

.. _levels:

Record levels
-------------

Lithoxyl has three built-in levels. In order of increasing importance:

* **debug** - Of interest to developers. Supplementary info for when something goes wrong.
* **info** - Informational. Can be helpful to know even when there are no problems.
* **critical** - Core functionality. Essential details at all times.

.. _status:

Record status
-------------

Lithoxyl Records are compact state machines. They go from creation to
beginning to completion (success, failure, exception).

First, simply creating a Record does not "begin" it. A record must be
entered with a **with** statement to become active. When a record
becomes active, it creates a beginning timestamp, and becomes the
immediate parent of future records, until one of those is entered and
begun.

Records can only "begin" once, leaving only completion to be
discussed. There are three completion states:

* **success** - The action described by the record completed without
  issue. This is the automatic default when no exception is raised.
* **failure** - The action did not complete successfully, and the
  failure was expected and/or handled within the application.
* **exception** - The action terminated unexpectedly, likely with a
  Python exception. This is the automatic default when an exception is
  raised within a record context manager.

Record API
----------

Records are usually constructed through Loggers, but it can help to
know the underlying API and see the obvious parallels.

.. autoclass:: lithoxyl.record.Record
   :members:


.. _concurrency:

Record concurrency
------------------

TODO
