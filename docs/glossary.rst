Glossary
========

.. todo: link to examples

.. glossary::
   :sorted:

   logger
     An instance of the :class:`~lithoxyl.logger.Logger` type, and one
     of the three fundamental Lithoxyl types. Responsible for
     facilitating the creation and publication of :term:`records
     <record>`. Generally there is one logger per aspect of an
     application. For example, a request logger and a database query
     logger.

   record
     An instance of the :class:`~lithoxyl.logger.Record` type, and one
     of the three fundamental Lithoxyl types. The :class:`Record` type
     is rarely instantiated directly, instead they are created by
     :term:`loggers <logger>`, manipulated, and automatically
     published to :term:`sinks <sink>`.

   status
     The completion state of a :term:`record`, meant to represent one
     of four possible task outcomes:

       * **Begin** - not yet completed
       * **Success** - no exceptions or failures
       * **Failure** - anticipated or application-level unsuccessful
         completion (e.g., invalid username)
       * **Exception** - unanticipated or lower-level unsuccessful
         completion (e.g., database connection interrupted)

   sink
     Any object implementing the Sink protocol, and one of the
     three fundamental Lithoxyl types. Typically subscribed to
     :term:`records <record>` by being attached to a
     :term:`logger`. Some basic types of sinks include record
     emitters, statistics collectors, and profilers.

   emitter
     A sink or other object capable of publishing record entries out
     of the process. Emitters commonly publish to network services,
     local services, and files.

   formatter
     An object responsible for transforming a :term:`record` into a
     string, ready to be encoded and :term:`emitted <emitter>`

   lithoxyl
     Mineralized wood.
