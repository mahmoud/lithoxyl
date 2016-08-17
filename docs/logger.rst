The Logger
==========

.. automodule:: lithoxyl.logger

.. autoclass:: lithoxyl.logger.Logger

Action creation
~~~~~~~~~~~~~~~

The Logger is primarily used through its
:class:`~lithoxyl.action.Action`-creating convenience methods named
after various log levels: :meth:`~Logger.debug`, :meth:`~Logger.info`,
and :meth:`~Logger.critical`.

Each creates a new :term:`action` with a given name, passing any
additional keyword arguments on through to the
:class:`lithoxyl.action.Action` constructor.

.. automethod:: lithoxyl.logger.Logger.debug
.. automethod:: lithoxyl.logger.Logger.info
.. automethod:: lithoxyl.logger.Logger.critical

The action level can also be passed in:

.. automethod:: lithoxyl.logger.Logger.action

Sink registration
~~~~~~~~~~~~~~~~~

Another vital aspect of Loggers is the :ref:`registration and
management of Sinks <configuring_sinks>`.

.. autoattribute:: lithoxyl.logger.Logger.sinks
.. automethod:: lithoxyl.logger.Logger.add_sink
.. automethod:: lithoxyl.logger.Logger.set_sinks
.. automethod:: lithoxyl.logger.Logger.clear_sinks

Event handling
~~~~~~~~~~~~~~

The event handling portion of the Logger API exists for Logger-Sink
interactions.

.. automethod:: lithoxyl.logger.Logger.on_begin
.. automethod:: lithoxyl.logger.Logger.on_end
.. automethod:: lithoxyl.logger.Logger.on_warn
.. automethod:: lithoxyl.logger.Logger.on_exception
