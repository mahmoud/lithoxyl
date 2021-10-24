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
    PY3 = False
except NameError:
    PY3 = True
    unicode = str

# TODO: not sure about RawIOBase
stream_types = (io.BytesIO, io.BufferedWriter, io.RawIOBase)
try:
    # py2
    import StringIO
    stream_types += (StringIO.StringIO, file)
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


def _get_sys_stream(name):
    stream = getattr(sys, name)
    # originally wanted to grab the buffer only on py3, but that
    # breaks pytest on py2, which relies on the buffer
    if PY3 or ('b' not in stream.mode and hasattr(stream, 'buffer')):
        stream = stream.buffer

    return stream


class StreamEmitter(object):
    '''Allows SensibleSinks to write to streams, be they StringIO or
    console (stdout/stderr).

    Avoid using StreamEmitter directly when you have a file path for
    your log file. Use FileEmitter instead.
    '''
    def __init__(self, stream, encoding=None, **kwargs):
        if encoding is None:
            encoding = getattr(stream, 'encoding', None) or 'UTF-8'
        errors = kwargs.pop('errors', 'backslashreplace')

        check_encoding_settings(encoding, errors)  # raises on error

        if stream in ('stdout', 'stderr'):
            stream = _get_sys_stream(stream)

        if not isinstance(stream, stream_types):
            st_names = ', '.join([st.__name__.lstrip('_') for st in stream_types])
            raise TypeError('%s expected instance of %s, or shortcut'
                            ' values "stderr" or "stdout", not: %r'
                            % (self.__class__.__name__, st_names, stream))
        _mode = getattr(stream, 'mode', None)
        if _mode and PY3 and 'b' not in _mode:
            raise ValueError('expected stream opened in binary mode, not: %r (mode %s)'
                             % (stream, _mode))
        self.stream = stream
        self._stream_name = getattr(self.stream, 'name', None)

        self.sep = kwargs.pop('sep', None)
        if self.sep is None:
            self.sep = os.linesep
        if isinstance(self.sep, unicode):
            self.sep = self.sep.encode(encoding)
        self.errors = errors
        self.encoding = encoding
        self._reopen_stale = kwargs.pop('reopen_stale', True)

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
            self.stream.write(entry + self.sep if self.sep else entry)
            self.flush()
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
                    self.stream = open(name, 'ab')

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
    """
    The convenient and correct way to write logs to a file when you have a path available.
    """
    def __init__(self, filepath, encoding='utf-8', **kwargs):
        self.filepath = os.path.abspath(filepath)
        mode = 'ab' if not kwargs.pop('overwrite', False) else 'wb'
        stream = io.open(self.filepath, mode)
        super(FileEmitter, self).__init__(stream, encoding=encoding, **kwargs)

    def close(self):
        if self.stream is None:
            return
        try:
            self.flush()
            if self.stream:
                self.stream.close()
                self.stream = None
        except Exception as e:
            note('file_close', 'got %r on %r.close()', e, self)
