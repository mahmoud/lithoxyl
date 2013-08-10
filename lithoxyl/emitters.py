# -*- coding: utf-8 -*-

import os
import sys


class StreamEmitter(object):
    def __init__(self, stream=None, linesep=os.linesep):
        if stream is None:
            stream = sys.stderr
        elif stream == 'stdout':
            stream = sys.stdout
        elif stream == 'stderr':
            stream = sys.stderr
        self.stream = stream
        self.linesep = linesep

    def emit_entry(self, entry):
        try:
            self.stream.write(entry)
            try:
                self.stream.write(self.linesep)
            except AttributeError:
                pass
        except:
            # TODO: something maybe
            raise

    __call__ = emit_entry
