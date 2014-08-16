# -*- coding: utf-8 -*-

from docker_registry.core import driver as driveengine
from docker_registry import testing
# Mock any boto
from docker_registry.testing import mock_boto  # noqa

# Mock our s3 - xxx this smells like byte-range support is questionnable...
from . import mock_s3   # noqa


def getinit(name):
    def init(self):
        self.scheme = name
        self.path = ''
        self.config = testing.Config({})
    return init

for name in driveengine.available():
    # The globals shenanigan is required so that the test tool find the tests
    # The dynamic type declaration is required because it is so
    globals()['TestQuery%s' % name] = type('TestQuery%s' % name,
                                           (testing.Query,),
                                           dict(__init__=getinit(name)))

    globals()['TestDriver%s' % name] = type('TestDriver%s' % name,
                                            (testing.Driver,),
                                            dict(__init__=getinit(name)))
