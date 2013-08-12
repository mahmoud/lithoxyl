# -*- coding: utf-8 -*-

import os
import sys

# TODO: should separators (i.e., newline) be handled here or in the Formatter?


class StreamEmitter(object):
    def __init__(self, stream=None, encoding=None, **kwargs):
        if stream is None:
            stream = sys.stderr
        elif stream == 'stdout':
            stream = sys.stdout
        elif stream == 'stderr':
            stream = sys.stderr
        self.stream = stream
        if encoding is None:
            encoding = getattr(stream, 'encoding', None) or 'UTF-8'
        self.encoding = encoding

        self.errors = kwargs.pop('errors', 'backslashreplace')
        self.newline = kwargs.pop('newline', None) or os.linesep

        # TODO: try values for encoding/errors/newline out (otherwise
        # problems can get detected way too late)
        # Relatedly, is it already too late by the time the Emitter
        # is initializing? That's probably up to the sink/logger.

    def emit_entry(self, entry):
        try:
            entry = entry.encode(self.encoding, self.errors)
        except UnicodeDecodeError:
            # Note that this is a *decode* error, meaning a bytestring
            # found its way through and implicit decoding is
            # happening.
            # TODO: configurable behavior for if bytes manage to find
            # their way through?
            raise
        try:
            self.stream.write(entry)
            if self.newline:
                self.stream.write(self.newline)
            self.flush()
        except:
            # TODO: something maybe
            # TODO: built-in logging raises KeyboardInterrupts and
            # SystemExits, special handling for everything else.
            raise

    def flush(self):
        #if callable(getattr(self.stream, 'flush', None)):
        if self.stream is None:
            return
        try:
            self.stream.flush()
        except:
            # TODO: warn
            pass

    __call__ = emit_entry


class FileEmitter(StreamEmitter):
    def __init__(self, filepath, encoding=None, **kwargs):
        self.filepath = os.path.abspath(filepath)
        self.mode = 'a'  # always 'a'?
        stream = open(self.filepath, self.mode)
        super(FileEmitter, self).__init__(stream, self.encoding, **kwargs)

    def close(self):
        if self.stream is None:
            return
        try:
            self.flush()
            self.stream.close()
        except:
            # TODO: warn
            pass


class WatchedFileEmitter(FileEmitter):
    def __init__(self, *a, **kw):
        # TODO: warn on windows usage
        super(WatchedFileEmitter, self).__init__(*a, **kw)
        try:
            stat = os.stat(self.filepath)
            self.dev, self.inode = stat.st_dev, stat.st_ino
        except OSError:
            # TODO: check errno? prolly not.
            self.dev, self.inode = None, None

    def emit(self, record):
        try:
            stat = os.stat(self.filepath)
            new_dev, new_inode = stat.st_dev, stat.st_ino
        except OSError:
            new_dev, new_inode = None, None
        is_changed = (new_dev, new_inode) != (self.dev, self.inode)
        if is_changed and self.stream is not None:
            self.close()
            self.stream = open(self.filepath, self.mode)
            stat = os.stat(self.filepath)
            self.dev, self.inode = stat.st_dev, stat.st_ino
        super(WatchedFileEmitter, self).emit(record)


class RotatingFileEmitter(FileEmitter):
    def __init__(self, filepath):
        pass
