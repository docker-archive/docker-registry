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

import logging
import math
import random
import string

from nose import tools

from ..core import compat
from ..core import driver
from ..core import exceptions

logger = logging.getLogger(__name__)


class Driver(object):

    def __init__(self, scheme=None, path=None, config=None):
        self.scheme = scheme
        self.path = path
        self.config = config

    # Load the requested driver
    def setUp(self):
        storage = driver.fetch(self.scheme)
        self._storage = storage(self.path, self.config)

    def tearDown(self):
        pass

    def gen_random_string(self, length=16):
        return ''.join([random.choice(string.ascii_uppercase + string.digits)
                        for x in range(length)]).lower()

    def simplehelp(self, path, content, expected, size=0):
        self._storage.put_content(path, content)
        assert self._storage.get_content(path) == expected
        assert self._storage.get_content(path) == expected
        if size:
            assert self._storage.get_size(path) == size

    def unicodehelp(self, path, content, expected):
        self._storage.put_unicode(path, content)
        assert self._storage.get_unicode(path) == expected
        assert self._storage.get_unicode(path) == expected

    def jsonhelp(self, path, content, expected):
        self._storage.put_json(path, content)
        assert self._storage.get_json(path) == expected
        assert self._storage.get_json(path) == expected

    def test_exists_non_existent(self):
        filename = self.gen_random_string()
        assert not self._storage.exists(filename)

    def test_exists_existent(self):
        filename = self.gen_random_string()
        self._storage.put_content(filename, b'')
        assert self._storage.exists(filename)

    # get / put
    def test_write_read_1(self):
        filename = self.gen_random_string()
        content = b'a'
        expected = b'a'
        self.simplehelp(filename, content, expected, len(expected))

    def test_write_read_2(self):
        filename = self.gen_random_string()
        content = b'\xc3\x9f'
        expected = b'\xc3\x9f'
        self.simplehelp(filename, content, expected, len(expected))

    def test_write_read_3(self):
        filename = self.gen_random_string()
        content = u'ß'.encode('utf8')
        expected = b'\xc3\x9f'
        self.simplehelp(filename, content, expected, len(expected))

    def test_write_read_4(self):
        filename = self.gen_random_string()
        content = 'ß'
        if compat.is_py2:
            content = content.decode('utf8')
        content = content.encode('utf8')
        expected = b'\xc3\x9f'
        self.simplehelp(filename, content, expected, len(expected))

    def test_write_read_5(self):
        filename = self.gen_random_string()
        content = self.gen_random_string().encode('utf8')
        expected = content
        self.simplehelp(filename, content, expected, len(expected))

    def test_write_read_6(self):
        filename = self.gen_random_string()
        content = self.gen_random_string(1024 * 1024).encode('utf8')
        expected = content
        self.simplehelp(filename, content, expected, len(expected))

    # get / put unicode
    def test_unicode_1(self):
        filename = self.gen_random_string()
        content = 'a'
        expected = u'a'
        self.unicodehelp(filename, content, expected)

    def test_unicode_2(self):
        filename = self.gen_random_string()
        content = b'\xc3\x9f'.decode('utf8')
        expected = u'ß'
        self.unicodehelp(filename, content, expected)

    def test_unicode_3(self):
        filename = self.gen_random_string()
        content = u'ß'
        expected = u'ß'
        self.unicodehelp(filename, content, expected)

    def test_unicode_4(self):
        filename = self.gen_random_string()
        content = 'ß'
        if compat.is_py2:
            content = content.decode('utf8')
        expected = u'ß'
        self.unicodehelp(filename, content, expected)

    def test_unicode_5(self):
        filename = self.gen_random_string()
        content = self.gen_random_string()
        expected = content
        self.unicodehelp(filename, content, expected)

    def test_unicode_6(self):
        filename = self.gen_random_string()
        content = self.gen_random_string(1024 * 1024)
        expected = content
        self.unicodehelp(filename, content, expected)

    # JSON
    def test_json(self):
        filename = self.gen_random_string()
        content = {u"ß": u"ß"}
        expected = {u"ß": u"ß"}
        self.jsonhelp(filename, content, expected)

    # Removes
    def test_remove_existent(self):
        filename = self.gen_random_string()
        content = self.gen_random_string().encode('utf8')
        self._storage.put_content(filename, content)
        self._storage.remove(filename)
        assert not self._storage.exists(filename)

    def test_remove_folder(self):
        dirname = self.gen_random_string()
        filename1 = self.gen_random_string()
        filename2 = self.gen_random_string()
        content = self.gen_random_string().encode('utf8')
        self._storage.put_content('%s/%s' % (dirname, filename1), content)
        self._storage.put_content('%s/%s' % (dirname, filename2), content)
        self._storage.remove(dirname)
        assert not self._storage.exists(filename1)
        assert not self._storage.exists(filename2)
        assert not self._storage.exists(dirname)
        # Check the lru is ok
        try:
            self._storage.get_content(filename1)
            assert False
        except Exception:
            pass

        try:
            self._storage.get_content(filename2)
            assert False
        except Exception:
            pass

    @tools.raises(exceptions.FileNotFoundError)
    def test_remove_inexistent(self):
        filename = self.gen_random_string()
        self._storage.remove(filename)

    @tools.raises(exceptions.FileNotFoundError)
    def test_read_inexistent(self):
        filename = self.gen_random_string()
        self._storage.get_content(filename)

    @tools.raises(exceptions.FileNotFoundError)
    def test_get_size_inexistent(self):
        filename = self.gen_random_string()
        self._storage.get_size(filename)

    def test_stream(self):
        filename = self.gen_random_string()
        # test 7MB
        content = self.gen_random_string(7).encode('utf8')  # * 1024 * 1024
        # test exists
        io = compat.StringIO(content)
        logger.debug("%s should NOT exists still" % filename)
        assert not self._storage.exists(filename)

        self._storage.stream_write(filename, io)
        io.close()

        logger.debug("%s should exist now" % filename)
        assert self._storage.exists(filename)

        # test read / write
        data = compat.bytes()
        for buf in self._storage.stream_read(filename):
            data += buf

        assert content == data

        # test bytes_range only if the storage backend suppports it
        if self._storage.supports_bytes_range:
            b = random.randint(0, math.floor(len(content) / 2))
            bytes_range = (b, random.randint(b + 1, len(content) - 1))
            data = compat.bytes()
            for buf in self._storage.stream_read(filename, bytes_range):
                data += buf
            expected_content = content[bytes_range[0]:bytes_range[1] + 1]
            assert data == expected_content

        # logger.debug("Content length is %s" % len(content))
        # logger.debug("And retrieved content length should equal it: %s" %
        #              len(data))
        # logger.debug("got content %s" % content)
        # logger.debug("got data %s" % data)

        # test remove
        self._storage.remove(filename)
        assert not self._storage.exists(filename)

    @tools.raises(exceptions.FileNotFoundError)
    def test_stream_read_inexistent(self):
        filename = self.gen_random_string()
        data = compat.bytes()
        for buf in self._storage.stream_read(filename):
            data += buf

    @tools.raises(exceptions.FileNotFoundError)
    def test_inexistent_list_directory(self):
        notexist = self.gen_random_string()
        iterator = self._storage.list_directory(notexist)
        next(iterator)

    # XXX only elliptics return StopIteration for now - though we should
    # return probably that for all
    @tools.raises(exceptions.FileNotFoundError, StopIteration)
    def test_empty_list_directory(self):
        path = self.gen_random_string()
        content = self.gen_random_string().encode('utf8')
        self._storage.put_content(path, content)

        iterator = self._storage.list_directory(path)
        next(iterator)

    def test_list_directory(self):
        base = self.gen_random_string()
        filename1 = self.gen_random_string()
        filename2 = self.gen_random_string()
        fb1 = '%s/%s' % (base, filename1)
        fb2 = '%s/%s' % (base, filename2)
        content = self.gen_random_string().encode('utf8')
        self._storage.put_content(fb1, content)
        self._storage.put_content(fb2, content)
        assert sorted([fb1, fb2]
                      ) == sorted(list(self._storage.list_directory(base)))

    # def test_root_list_directory(self):
    #     fb1 = self.gen_random_string()
    #     fb2 = self.gen_random_string()
    #     content = self.gen_random_string()
    #     self._storage.put_content(fb1, content)
    #     self._storage.put_content(fb2, content)
    #     print(list(self._storage.list_directory()))
    #     assert sorted([fb1, fb2]
    #                   ) == sorted(list(self._storage.list_directory()))

    @tools.raises(exceptions.FileNotFoundError, StopIteration)
    def test_empty_after_remove_list_directory(self):
        base = self.gen_random_string()
        filename1 = self.gen_random_string()
        filename2 = self.gen_random_string()
        fb1 = '%s/%s' % (base, filename1)
        fb2 = '%s/%s' % (base, filename2)
        content = self.gen_random_string().encode('utf8')
        self._storage.put_content(fb1, content)
        self._storage.put_content(fb2, content)

        self._storage.remove(fb1)
        self._storage.remove(fb2)

        iterator = self._storage.list_directory(base)
        next(iterator)

    def test_paths(self):
        namespace = 'namespace'
        repository = 'repository'
        tag = 'sometag'
        image_id = 'imageid'
        p = self._storage.images_list_path(namespace, repository)
        assert not self._storage.exists(p)
        p = self._storage.image_json_path(image_id)
        assert not self._storage.exists(p)
        p = self._storage.image_mark_path(image_id)
        assert not self._storage.exists(p)
        p = self._storage.image_checksum_path(image_id)
        assert not self._storage.exists(p)
        p = self._storage.image_layer_path(image_id)
        assert not self._storage.exists(p)
        p = self._storage.image_ancestry_path(image_id)
        assert not self._storage.exists(p)
        p = self._storage.image_files_path(image_id)
        assert not self._storage.exists(p)
        p = self._storage.image_diff_path(image_id)
        assert not self._storage.exists(p)
        p = self._storage.repository_path(namespace, repository)
        assert not self._storage.exists(p)
        p = self._storage.tag_path(namespace, repository)
        assert not self._storage.exists(p)
        p = self._storage.tag_path(namespace, repository, tag)
        assert not self._storage.exists(p)
        p = self._storage.repository_json_path(namespace, repository)
        assert not self._storage.exists(p)
        p = self._storage.repository_tag_json_path(namespace, repository, tag)
        assert not self._storage.exists(p)
        p = self._storage.index_images_path(namespace, repository)
        assert not self._storage.exists(p)
        p = self._storage.private_flag_path(namespace, repository)
        assert not self._storage.exists(p)
