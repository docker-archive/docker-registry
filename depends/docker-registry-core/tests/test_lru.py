# -*- coding: utf-8 -*-
# Copyright (c) 2014 Docker.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from docker_registry.core import compat
from docker_registry.core import lru

# In case you want to mock (and that doesn't work well)
# import mock
# import mockredis
# @mock.patch('docker_registry.core.lru.redis.StrictRedis',
#             mockredis.mock_strict_redis_client)
# def boot():
#     lru.init()

# boot()

lru.init()


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

    def setUp(self):
        self._dumb = Dumb()

    def testNonExistentGet(self):
        assert not self._dumb.get('nonexistent')
        assert not self._dumb.get('nonexistent')

    def testSetSimple1(self):
        content = 'bar'
        result = b'bar'
        self._dumb.set('foo', content)
        assert self._dumb.get('foo') == result
        assert self._dumb.get('foo') == result

    def testSetBytes1(self):
        content = b'foo'
        result = b'foo'
        self._dumb.set('foo', content)
        assert self._dumb.get('foo') == result

    def testSetBytes2(self):
        content = b'\xc3\x9f'
        result = b'\xc3\x9f'
        self._dumb.set('foo', content)
        assert self._dumb.get('foo') == result

    def testSetUnicode1(self):
        content = u'foo'
        result = b'foo'
        self._dumb.set('foo', content)
        assert self._dumb.get('foo') == result

    def testSetUnicode2(self):
        content = u'ß'
        result = b'\xc3\x9f'
        self._dumb.set('foo', content)
        assert self._dumb.get('foo') == result

    def testSetUnicode3(self):
        content = u'ß'.encode('utf8')
        result = b'\xc3\x9f'
        self._dumb.set('foo', content)
        assert self._dumb.get('foo') == result

    def testSetUnicode4(self):
        content = 'ß'
        if compat.is_py2:
            content = content.decode('utf8')
        content = content.encode('utf8')
        result = b'\xc3\x9f'
        self._dumb.set('foo', content)
        assert self._dumb.get('foo') == result

    def testRemove(self):
        self._dumb.set('foo', 'bar')
        assert self._dumb.get('foo')
        self._dumb.remove('foo')
        assert not self._dumb.get('foo')
        assert not self._dumb.get('foo')
