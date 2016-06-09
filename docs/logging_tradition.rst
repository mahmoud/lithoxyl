The Logging Tradition
=====================

For experienced engineers, it can help to understand Lithoxyl by
taking a hard look at the past and current state of logging.

Logging in General
------------------

Without getting into Python specifics, most ecosystems have pretty low
standards for logging. Logging is an afterthought, added when the
application misbehaves and needs to be debugged. Just having *any*
logging can easily put an application in the top quartile for quality.

And worse yet, the opposite can be true. Logging's place in software
is so low that having logging is often a yellow flag for lower-quality
code in need of constant debugging. If the code needed so much
logging, it must have had a lot of problems.

This is the past and present reality of logging in general.

Logging in Python
-----------------

This will be frank, so first things first: all due respect to Vinay
Sajip and all the Python contributors who worked on Python
logging. Without their work, there is no telling where we would be
today. Now, the critique.

The built-in :mod:`logging` module itself followed this afterthought
pattern. Little more than a knockoff of `Log4j`_, ``logging`` pays
virtually no mind to performance, practicality, or the fact that
*Python is not Java*.

Application instrumentation is important. Good metrics are worth more
than their weight in CPU cycles. By running a high-level language like
Python, a design decision has already been made to achieve a richer,
more featureful environment.

With that in mind, it is critical that Python libraries take the
semantic high road. Always emphasize maintainability,
introspectability, and reliability in Python code.

Because application instrumentation is vital to all these areas, the
approach and framework used *must* be closely matched. The built-in
:class:`logging` library is a frumpy, secondhand suit, thrifted and
worn without even a thorough cleaning. Lithoxyl is new, tailored to
fit Python and its many, many modern applications.

.. _Log4j: http://logging.apache.org/log4j/1.2/

.. more like we need something more formal, like a tuxedo, and instead
   we got a pitstained tshirt with a tuxedo printed on it. and the
   pitstains aren't even ours.

The Lithoxyl Response
---------------------

Python's power lets us do better. And we can't stop with just
logging. We need to look at instrumentation as a whole.

Tradition is to add logging to indicate breakage. Little more than
print statements and tracebacks piped to files.

Modern instrumentation is more than a debugging utility.

Lithoxyl provides structured data and online statistics to unlock your
application's potential. Lithoxyl is a development tool, worth using
from day one. Good instrumentation focuses on the whole application
lifecycle. It helps with debugging problems, but it also offers
direction when the sun is shining and the monitoring is
green. Lithoxyl is the Pythonic step toward that bright,
introspectable future.
