Frequently Asked Questions
==========================

Lithoxyl's new approach answers quite a lot of questions, but raises a
few others. These questions fall into two categories, `Design
<#design-questions>`_ and `Background <#background-questions>`_.

Design questions
----------------

Some questions are hard because they are ultimately decided by your
application's design. Lithoxyl is mostly an API to
instrumentation. There are many right ways.

What is the difference between failure status and exception status?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There are a couple angles to answer this. First, it is pretty rare to
set an exception status manually, as exception information is usually
populated automatically when there are uncaught exceptions. That
contrasts with :meth:`~Action.failure`, which is seen more often.

So when to call :meth:`~Action.failure`? As with many design
questions, an example is often best. With an HTTP server, returning a
4xx or even a 503 can be viewed as failures outside of the control of
the application, which is performing fine. A 500, on the other hand,
is generally unexpected and deserves an exception status.

Why does Lithoxyl sometimes fail silently?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Built-in to the design of Lithoxyl itself, there are several
deviations from what one might consider standard practice. With most
libraries, one expects that code will "fail fast". However, failing
fast does not work well for instrumentation code.

Lithoxyl assumes that you are instrumenting a system which has
behavior other than logging and statistics collection. Your system's
primary functions take priority. Instrumentation must degrade
gracefully.

This means if your message is malformed Lithoxyl will do its best to
output the most that it can and no exception will be raised. If your
logging service is down, maybe the Sink queues the message, but
eventually that queues bounds will be overrun and messages may
silently drop.

This graceful degradation takes place at all the runtime integration
points, i.e., action usage within your application code. For Sink and
Logger configuration, actions which are typically performed at startup
and import time, exceptions are still raised as usual. In fact, it is
considered good Lithoxyl practice to forward-check these
configurations. This means checking that callable arguments are

If you discover a runtime scenario that should degrade with more grace
or a configuration-time scenario which could prevent runtime failures
through more forward checking, please do file an issue.

Background questions
--------------------

Unlike the design questions above, background questions relate to just
the objective facts.

.. _etymology:

What's with the name, Lithoxyl, what's that even mean?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Lithoxyl is a geological term for petrified wood. Fossilized
trees. Rock-solid logs.

.. TODO: image
