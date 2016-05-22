Frequently Asked Questions
==========================

Lithoxyl's many powerful paradigms mean that there is plenty to
learn. Here are a few of the questions that pop up more than others.

Hard questions
--------------

Some questions are hard because they are ultimately decided by your
application's design. Lithoxyl is mostly an API to
instrumentation. There are many right ways.

What is the difference between failure status and exception status?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There are a couple angles to answer this. First, it is pretty rare to
set an exception status manually, as exception information is usually
populated automatically when there are uncaught exceptions. That
contrasts with :meth:`~Record.failure`, which is seen more often.

So when to call :meth:`~Record.failure`? As with many design
questions, an example is often best. With an HTTP server, returning a
4xx or even a 503 can be viewed as failures outside of the control of
the application, which is performing fine. A 500, on the other hand,
is generally unexpected and deserves an exception status.

Easy questions
--------------

Other questions are pretty straightforward.

.. ref:: etymology

What's with the name, Lithoxyl, what's that even mean?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Lithoxyl is a geological term for petrified wood. Fossilized
trees. Rock-solid logs.

.. TODO: image
