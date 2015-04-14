The Current State of Logging
============================

For experienced engineers, it may be best to understand lithoxyl by
first taking a hard look at the current state of logging, with a focus
on logging in Python.

Logging in Python
-----------------

First, because this will be blunt: all due respect to Vinay Sajip and
all the Python contributors who worked on Python logging. Without
their work, there is no telling where we would be today.

The built-in :mod:`logging` module is nothing more than a knockoff of
`Log4j`_, with virtually no mind paid to performance, practicality, or
the fact that *Python is not Java*.

Application instrumentation is important. Performance overhead is
more than acceptable, provided a rich return. There are many
legitimate cases where more time would is spent in instrumentation
code than in business logic. Simply remember that already by writing
and running Python, a trade has already been made to achieve greater a
richer, more featureful runtime environment.

With that trade already made, it is critical to always take the
semantic high road. Always emphasize maintainability,
introspectability, and reliability in Python code. And because
application instrumentation is vital to all these areas, the approach
and framework used *must* be closely tailored. The built-in
:class:`logging` library is a frumpy, store-bought suit, thrifted
and worn without even a thorough dry cleaning.

.. _Log4j: http://logging.apache.org/log4j/1.2/

.. more like we need something more formal, like a tuxedo, and instead
   we got a pitstained tshirt with a tuxedo printed on it. and the
   pitstains aren't even ours.

Logging in General
------------------

* Standards are low
* Application instrumentation usually begins and ends at logging
* Just by having any logging, an application is already in the top quartile for application instrumentation
* Logging is mostly for debugging purposes, added as an afterthought when the application misbehaves

From day one, instrumentation should focus on the whole application
lifecycle. Not just how to fix an application where and when it
breaks, but also how to improve it when all systems are working.
