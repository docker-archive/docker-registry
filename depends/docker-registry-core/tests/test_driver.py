# -*- coding: utf-8 -*-

from docker_registry.testing import Driver
from docker_registry.testing import Query


class TestQuery(Query):
    def __init__(self):
        self.scheme = 'dumb'


class TestDriver(Driver):
    def __init__(self):
        self.scheme = 'dumb'
        self.path = ''
        self.config = None
