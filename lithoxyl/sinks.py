# -*- coding: utf-8 -*-


class AggSink(object):
    def __init__(self):
        self.messages = []

    def handle_start(self, message):
        pass

    def handle(self, message):
        self.messages.append(message)
