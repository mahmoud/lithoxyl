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
        if isinstance(entry, unicode):
            entry = entry.encode(self.encoding, self.errors)
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
        if callable(getattr(self.stream, 'flush', None)):
            self.stream.flush()

    __call__ = emit_entry


class FileEmitter(StreamEmitter):
    def __init__(self, filepath, encoding=None, **kwargs):
        self.filepath = os.path.abspath(filepath)
        self.mode = 'a'  # always 'a'?
        stream = open(self.filepath, self.mode)
        super(FileEmitter, self).__init__(stream, self.encoding, **kwargs)

    def close(self):
        # TODO
        pass


class RotatingFileEmitter(FileEmitter):
    def __init__(self, filepath):
        pass
