# -*- coding: utf-8 -*-

from mock import patch
from mockredis import mock_strict_redis_client

from docker_registry.core import lru


class Dumb(object):

    value = {}

    @lru.get
    def get(self, key):
        if key not in self.value:
            return None
        return self.value[key]

    @lru.set
    def set(self, key, value):
        self.value[key] = value

    @lru.remove
    def remove(self, key):
        if key not in self.value:
            return
        del self.value[key]


class TestLru(object):

    @patch('docker_registry.core.lru.redis.StrictRedis',
           mock_strict_redis_client)
    def setUp(self):
        lru.init()
        self._dumb = Dumb()

    def testNonExistentGet(self):
        assert not self._dumb.get('nonexistent')

    def testNonExistentGetTwice(self):
        assert not self._dumb.get('nonexistent')
        assert not self._dumb.get('nonexistent')

    def testSetSimple(self):
        self._dumb.set('foo', 'bar')
        assert self._dumb.get('foo') == 'bar'
        assert self._dumb.get('foo') == 'bar'

    def testSetComplex(self):
        content = u"∫".encode('utf8')
        self._dumb.set('foo', content)
        assert self._dumb.get('foo') == content
        assert self._dumb.get('foo') == content

        content = "∫"
        self._dumb.set('foo', content)
        assert self._dumb.get('foo') == content
        assert self._dumb.get('foo') == content

        content = b"a"
        self._dumb.set('foo', content)
        assert self._dumb.get('foo') == content
        assert self._dumb.get('foo') == content

    def testRemove(self):
        self._dumb.set('foo', 'bar')
        assert self._dumb.get('foo')
        self._dumb.remove('foo')
        assert not self._dumb.get('foo')
