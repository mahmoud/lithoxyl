# -*- coding: utf-8 -*-
"""Emitters are callable objects which take an entry in *text-form*
and output it to a persistence resource, such as stdout/stderr, files,
or network streams.
"""

import os
import sys

from context import note

try:
    # unix only
    from _syslog_emitter import SyslogEmitter
except ImportError:
    pass


class EncodingLookupError(LookupError):
    pass


class ErrorBehaviorLookupError(LookupError):
    pass


def check_encoding_settings(encoding, errors):
    try:
        # then test error-handler
        u''.encode(encoding)
    except LookupError as le:
        raise EncodingLookupError(le.message)
    try:
        # then test error-handler
        u'\xdd'.encode('ascii', errors=errors)
    except LookupError as le:
        raise ErrorBehaviorLookupError(le.message)
    except Exception:
        return


class FakeEmitter(object):
    def __init__(self):
        self.entries = []

    def emit_entry(self, record, entry):
        self.entries.append((record, entry))

    on_begin = on_warn = on_complete = emit_entry


# TODO: rename StreamLineEmitter
class StreamEmitter(object):
    def __init__(self, stream, encoding=None, **kwargs):
        if stream == 'stdout':
            stream = sys.stdout
        elif stream == 'stderr':
            stream = sys.stderr
        elif not callable(getattr(stream, 'write', None)):
            raise TypeError('StreamEmitter expected file-like object'
                            ' (or shortcut values "stderr" or "stdout"),'
                            ' not %r' % stream)
        self.stream = stream
        if encoding is None:
            encoding = getattr(stream, 'encoding', None) or 'UTF-8'
        errors = kwargs.pop('errors', 'backslashreplace')

        check_encoding_settings(encoding, errors)  # raises on error

        self.newline = kwargs.pop('newline', None) or os.linesep
        self.errors = errors
        self.encoding = encoding

    def emit_entry(self, record, entry):
        try:
            entry = entry.encode(self.encoding, self.errors)
        except UnicodeDecodeError as ude:
            # Note that this is a *decode* error, meaning a bytestring
            # found its way through and implicit decoding is happening.
            note('emit_encode', 'got %r on %s.emit_entry();'
                 ' expected decoded text, not %r', ude, self, entry)
            raise
        try:
            self.stream.write(entry)
            if self.newline:
                self.stream.write(self.newline)
            self.flush()
        except Exception as e:
            note('stream_emit', 'got %r on %r.emit_entry()', e, self)

    on_begin = on_warn = on_complete = emit_entry

    def flush(self):
        # if callable(getattr(self.stream, 'flush', None)):
        if self.stream is None:
            return
        try:
            self.stream.flush()
        except Exception as e:
            note('stream_flush', 'got %r on %r.flush()', e, self)

    def __repr__(self):
        return '<%s stream=%r>' % (self.__class__.__name__, self.stream)


class FileEmitter(StreamEmitter):
    def __init__(self, filepath, encoding=None, **kwargs):
        self.filepath = os.path.abspath(filepath)
        self.encoding = encoding
        self.mode = 'a'  # always 'a'?
        stream = open(self.filepath, self.mode)
        super(FileEmitter, self).__init__(stream, self.encoding, **kwargs)

    def close(self):
        if self.stream is None:
            return
        try:
            self.flush()
            self.stream.close()
        except Exception as e:
            note('file_close', 'got %r on %r.close()', e, self)
