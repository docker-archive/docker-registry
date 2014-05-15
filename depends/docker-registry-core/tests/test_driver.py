# -*- coding: utf-8 -*-

from docker_registry import testing


class TestQuery(testing.Query):
    def __init__(self):
        self.scheme = 'dumb'


class TestDriver(testing.Driver):
    def __init__(self):
        self.scheme = 'dumb'
        self.path = ''
        self.config = None
