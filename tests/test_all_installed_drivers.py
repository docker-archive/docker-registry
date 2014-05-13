# -*- coding: utf-8 -*-

from docker_registry.core import driver as driveengine

from docker_registry.testing import Config
from docker_registry.testing import Driver
from docker_registry.testing import Query


def getinit(name):
    def init(self):
        self.scheme = name
        self.path = ''
        self.config = Config({})
    return init

for name in driveengine.available():
    # The globals shenanigan is required so that the test tool find the tests
    # The dynamic type declaration is required because it is so
    globals()['TestQuery%s' % name] = type('TestQuery%s' % name, (Query,),
                                           dict(__init__=getinit(name)))

    globals()['TestDriver%s' % name] = type('TestDriver%s' % name, (Driver,),
                                            dict(__init__=getinit(name)))
