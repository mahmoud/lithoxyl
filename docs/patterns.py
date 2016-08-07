"""\
For the moment, this module is a place to collect patterns, mostly
formats, from existing implementations and standards, so as to make
lithoxyl more immediately useful/usable.
"""

"""\

Lithoxyl is unlikely to go very far beyond providing basic formatting
utilities, most likely a few formatting helpers and format
strings. For the moment, I'm going to use new-style format strings.

Here's a list of values provided by Python's built-in logging library
for creating a formatted message, along with desirability wrt Lithoxyl:

 * args - all the args - no
 * asctime - formatted time - yes, but no. time formats should be more
 explicit
 * created - time.time() of record creation - yes, (Record.begin_time)
 * exc_info - exception tuple or none - yes
 * filename - filename of module issuing the logging call - maybe/probably
 * funcName - name of function making the call - maybe/probably
 * levelname - text version of level - yes
 * levelno - numeric version of level - yes
 * lineno - source line of logging call - maybe/probably
 * module - module from whence logging was called - maybe/probably
 * msecs - millisecond portion of message creation time - no
 * message - formatted message (msg % args) - maybe
 * msg - the format-string form of the message - yes
 * name - logger name - yes
 * pathname - full path name to source file of logging call - maybe/probably
 * process - pid - probably not
 * processName - (obvs) - probably not
 * relativeCreated - time in millisecond between creation and module load - no
 * thread - thread id - probably not
 * threadName - (obvs) - probably not
"""

"""
Apache access log:

  1.202.218.21 - - [22/Jun/2013:06:41:43 -0700] "GET /robots.txt HTTP/1.1" 200 26

  Time format: [day/month/year:hour:minute:second zone]

Nginx default access log:

  78.178.243.200 - - [22/Jun/2013:15:02:31 -0700] "GET /favicon.ico HTTP/1.1" 404 570 "-" "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.116 Safari/537.36" "-"

  119.63.193.132 - - [22/Jun/2013:14:19:36 -0700] "GET / HTTP/1.1" 200 9755 "-" "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0)" "-"


Internet time format (RFC3339, ISO8601 compatible):

  1985-04-12T23:20:50.52Z
  1996-12-19T16:39:57-08:00

.. note::

   If the time in UTC is known, but the offset to local time is unknown,
   this can be represented with an offset of "-00:00"

Output of the ``date`` command (aka asctime()):

  Sat Jun 22 15:25:38 PDT 2013

RFC 822 date format (i.e., HTTP headers) (always GMT/UTC):

  Sun, 06 Nov 1994 08:49:37 GMT
"""
