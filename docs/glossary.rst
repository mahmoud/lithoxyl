Glossary
========

.. todo: link to examples

.. glossary::
   :sorted:

   logger
     An instance of the :class:`~lithoxyl.logger.Logger`
     type. Responsible for facilitating the creation and publication
     of :term:`actions <action>`. Generally there is one logger per
     aspect of an application. For example, a request logger and a
     database query logger.

   action
     An instance of the :class:`~lithoxyl.logger.Action` type, and one
     of the three fundamental Lithoxyl types. The :class:`Action` type
     is rarely instantiated directly, instead they are created by
     :term:`loggers <logger>`, manipulated, and automatically
     published to :term:`sinks <sink>`.

   status
     The completion state of an :term:`action`, meant to represent one
     of four possible task outcomes:

       * **Begin** - not yet completed
       * **Success** - no exceptions or failures
       * **Failure** - anticipated or application-level unsuccessful
         completion (e.g., invalid username)
       * **Exception** - unanticipated or lower-level unsuccessful
         completion (e.g., database connection interrupted)

   event

     An occurence associated with a Logger and Action. One of:

       * **begin** - The start of an Action.
       * **end** - The completion of an Action (success, failure, or exception)
       * **warn** - A warning related to an Action.
       * **comment** - A metadata event associated with a Logger
       * **exception** - An unhandled exception during an Action.

     :term:`Sinks <sink>` implement methods to handle each of these events.

   sink
     Any object implementing the Sink protocol for handling
     :term:`events <event>`. Typically subscribed to :term:`actions
     <action>` by being attached to a :term:`logger`. Some basic types
     of sinks include action emitters, statistics collectors, and
     profilers.

   emitter
     An object capable of publishing formatted messages out of the
     process. Emitters commonly publish to network services, local
     services, and files. The last step in the Sensible
     Filter-Format-Emit logging process.

   formatter
     An object responsible for transforming a :term:`action` into a
     string, ready to be encoded and :term:`emitted <emitter>`

   lithoxyl
     Mineralized wood.

   with
     Python's compact context manager syntax, roughly approximating a
     "try-finally" block. With blocks have *enter* and *exit* hooks
     that enable tracking of Action events, no matter whether the
     wrapped code executes successfully or raises an exception.
