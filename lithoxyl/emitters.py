# -*- coding: utf-8 -*-
"""Emitters are callable objects which take an entry in *text-form*
and output it to a persistence resource, such as stdout/stderr, files,
or network streams.
"""

from __future__ import absolute_import
import io
import os
import sys
import errno
from collections import deque

from lithoxyl.context import note
from lithoxyl.utils import check_encoding_settings

try:
    # unix only
    from lithoxyl._syslog_emitter import SyslogEmitter
except ImportError:
    pass

try:
    unicode
except NameError:
    unicode = str


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
        if encoding is None:
            encoding = getattr(stream, 'encoding', None) or 'UTF-8'
        errors = kwargs.pop('errors', 'backslashreplace')

        check_encoding_settings(encoding, errors)  # raises on error

        if stream == 'stdout':
            stream = sys.stdout
        elif stream == 'stderr':
            stream = sys.stderr

        self._own_stream = False
        if isinstance(stream, io.RawIOBase):
            stream = io.TextIOWrapper(stream, encoding=encoding, errors=errors)
            self._own_stream = True

        if not isinstance(stream, io.TextIOWrapper):
            raise TypeError('StreamEmitter expected instance of TextIOWrapper or'
                            ' RawIOBase (or shortcut values "stderr" or "stdout"),'
                            ' not %r' % stream)
        self.stream = stream
        self._stream_name = getattr(self.stream, 'name', None)

        self.sep = kwargs.pop('sep', None)
        if self.sep is None:
            self.sep = os.linesep
        if isinstance(self.sep, bytes):
            self.sep = self.sep.decode(encoding)
        self.errors = errors
        self.encoding = encoding
        self._reopen_stale = kwargs.pop('reopen_stale', True)

    def __del__(self):
        if not getattr(self, '_own_stream', False):
            return
        try:
            self.stream.detach()
        except Exception:
            pass

    def emit_entry(self, event, entry):
        try:
            self.stream.write(entry + self.sep if self.sep else entry)
            self.flush()
        except UnicodeDecodeError as ude:
            # Note that this is a *decode* error, meaning a bytestring
            # found its way through and implicit decoding is happening.
            note('emit_encode', 'got %r on %s.emit_entry();'
                 ' expected decoded text, not %r', ude, self, entry)
            raise
        except Exception as e:
            note('stream_emit', 'got %r on %r.emit_entry()', e, self)
            if (type(e) is IOError
                and self._reopen_stale
                and getattr(e, 'errno', None)
                and e.errno == errno.ESTALE):
                name = self._stream_name
                if name and name not in ('<stdout>', '<stderr>'):
                    # NB: Stale file handles are pretty common on
                    # network file systems, so we try to reopen the file
                    note('stream_emit', 'reopening stale stream to %r', name)
                    # append in binary mode if the original mode was binary
                    mode = 'a' if 'b' in getattr(self.stream, 'mode', 'ab') else 'a'
                    self.stream = open(name, mode)

                    # retry writing once
                    self.stream.write(entry + self.sep if self.sep else entry)
                    self.flush()
        return

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
        self.mode = 'a' if not kwargs.pop('overwrite', False) else 'w'
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
