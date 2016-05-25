The Logging Tradition
=====================

For experienced engineers, it may be best to understand lithoxyl by
first taking a hard look at the past and current state of logging,
with a focus on logging in Python.

Logging in General
------------------

Before getting into Python, most ecosystems have pretty low standards for
logging. Logging is an afterthought, added when the application
misbehaves and needs to be debugged. Just having *any* logging can put
an application in the top quartile for quality. But so low is
logging's station that having logging can also be a yellow flag for
lower-quality code in need of constant debugging.


Logging in Python
-----------------

This will be frank, so first things first: all due respect to Vinay
Sajip and all the Python contributors who worked on Python
logging. Without their work, there is no telling where we would be
today. Now, the critique.

The built-in :mod:`logging` module is little more than a knockoff of
`Log4j`_, with virtually no mind paid to performance, practicality, or
the fact that *Python is not Java*.

Application instrumentation is important. Performance overhead is more
than acceptable, provided a rich return. There are many legitimate
cases where more time would is spent in instrumentation code than in
business logic. Remember that by running a high-level language like
Python, a trade has already been made to achieve greater a richer,
more featureful environment.

With that foregone conclusion, it is critical to always take the
semantic high road. Always emphasize maintainability,
introspectability, and reliability in Python code. And because
application instrumentation is vital to all these areas, the approach
and framework used *must* be closely matched. The built-in
:class:`logging` library is a frumpy, second-hand suit, thrifted and
worn without even a thorough cleaning. Lithoxyl is new, tailored to fit
Python and its many, many modern applications.

.. _Log4j: http://logging.apache.org/log4j/1.2/

.. more like we need something more formal, like a tuxedo, and instead
   we got a pitstained tshirt with a tuxedo printed on it. and the
   pitstains aren't even ours.

The Lithoxyl Response
---------------------

Python's power lets us do better. And we can't stop with just
logging. We need to look at the instrumentation as a whole.

Output must be more than print statements piped to files. Structured
data and online statistics unlock your application's potential.

Instrumentation is a development tool, worth using from day
one. Logging is mostly added to indicate breakage. However, good
instrumentation focuses on the whole application lifecycle. It helps
with debugging problems, and it also offers direction when the sun is
shining and the monitoring is showing all green.
