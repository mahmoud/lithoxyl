The Current State of Logging
============================

It's impossible to understand lithoxyl without taking a hard look at
the current state of logging, with a focus on logging in Python. To
put it bluntly, the built-in :mod:`logging` module is nothing more
than a knockoff of Log4J, with virtually no mind paid to performance,
practicality, or the fact that Python is not Java.

Application instrumentation is important. Performance overhead is more
than acceptable, provided a rich return. There are many legitimate
cases where more time would is spent in instrumentation code than in
business logic. Simply remember that already by writing and running
Python, a trade has already been made to achieve greater a richer,
more featureful runtime environment.

With that trade already made, it is critical to always take the
semantic high road. Always emphasize maintainability,
introspectability, and reliability in Python code. And because
application instrumentation is vital to all these areas, the approach
and framework used must be closely tailored. The built-in
:class:`logging` library is a decades-old, store-bought suit, thrifted
and worn without even a thorough dry cleaning.
