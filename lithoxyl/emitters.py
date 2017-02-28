# -*- coding: utf-8 -*-
"""Emitters are callable objects which take an entry in *text-form*
and output it to a persistence resource, such as stdout/stderr, files,
or network streams.
"""

import os
import sys
from collections import deque

from lithoxyl.context import note
from lithoxyl.utils import check_encoding_settings

try:
    # unix only
    from lithoxyl._syslog_emitter import SyslogEmitter
except ImportError:
    pass


class AggregateEmitter(object):
    def __init__(self, limit=None):
        self._limit = limit
        self.items = deque(maxlen=limit)

    def get_entries(self):
        return [entry for event, entry in self.items]

    def get_entry(self, idx):
        return self.items[idx][1]

    def clear(self):
        self.items.clear()

    def emit_entry(self, event, entry):
        self.items.append((event, entry))

    on_begin = on_warn = on_end = on_comment = emit_entry

    def __repr__(self):
        cn = self.__class__.__name__
        args = (cn, self._limit, len(self.items))
        msg = '<%s limit=%r entry_count=%r>' % args
        return msg


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

        self.sep = kwargs.pop('sep', None)
        if self.sep is None:
            self.sep = os.linesep
        self.errors = errors
        self.encoding = encoding

    def emit_entry(self, event, entry):
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
            if self.sep:
                self.stream.write(self.sep)
            self.flush()
        except Exception as e:
            note('stream_emit', 'got %r on %r.emit_entry()', e, self)

    on_begin = on_warn = on_end = on_comment = emit_entry

    def flush(self):
        stream_flush = getattr(self.stream, 'flush', None)
        if not callable(stream_flush):
            return
        try:
            stream_flush()
        except Exception as e:
            note('stream_flush', 'got %r on %r.flush()', e, self)

    def __repr__(self):
        return '<%s stream=%r>' % (self.__class__.__name__, self.stream)


class FileEmitter(StreamEmitter):
    def __init__(self, filepath, encoding=None, **kwargs):
        self.filepath = os.path.abspath(filepath)
        self.encoding = encoding
        self.mode = 'a'
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
