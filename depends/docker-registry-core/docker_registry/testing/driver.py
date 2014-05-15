# -*- coding: utf-8 -*-

import random
import string

from nose.tools import raises

from ..core import compat
from ..core import driver
from ..core import exceptions


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

    def test_exists_non_existent_path(self):
        filename = self.gen_random_string()
        assert not self._storage.exists(filename)

    def test_exists_existent_path(self):
        filename = self.gen_random_string()
        content = self.gen_random_string().encode('utf8')
        self._storage.put_content(filename, content)
        assert self._storage.exists(filename)

    def test_write_read(self):
        filename = self.gen_random_string()
        content = self.gen_random_string().encode('utf8')
        self._storage.put_content(filename, content)

        ret = self._storage.get_content(filename)
        assert ret == content

    def test_size(self):
        filename = self.gen_random_string()
        content = self.gen_random_string().encode('utf8')
        self._storage.put_content(filename, content)

        ret = self._storage.get_size(filename)
        assert ret == len(content)

    def test_write_read_unicode(self):
        filename = self.gen_random_string()

        content = u"∫".encode('utf8')
        self._storage.put_content(filename, content)

        ret = self._storage.get_content(filename)
        assert ret == content
        ret = self._storage.get_size(filename)
        assert ret == len(content)

    def test_write_read_unicode_str(self):
        filename = self.gen_random_string()

        content = "∫"
        if compat.is_py2:
            content = content.decode('utf8')
        content = content.encode('utf8')
        self._storage.put_content(filename, content)

        ret = self._storage.get_content(filename)
        assert ret == content
        ret = self._storage.get_size(filename)
        assert ret == len(content)

    def test_write_read_bytes(self):
        filename = self.gen_random_string()

        content = b"a"
        self._storage.put_content(filename, content)

        ret = self._storage.get_content(filename)
        assert ret == content
        ret = self._storage.get_size(filename)
        assert ret == len(content)

    def test_write_read_twice(self):
        filename = self.gen_random_string()
        content = self.gen_random_string().encode('utf8')
        self._storage.put_content(filename, content)
        ret = self._storage.get_content(filename)
        l = self._storage.get_size(filename)

        content2 = self.gen_random_string().encode('utf8')
        self._storage.put_content(filename, content2)
        ret2 = self._storage.get_content(filename)
        l2 = self._storage.get_size(filename)

        assert ret == content
        assert l == len(content)
        assert ret2 == content2
        assert l2 == len(content2)

    def test_remove_existent(self):
        filename = self.gen_random_string()
        content = self.gen_random_string().encode('utf8')
        self._storage.put_content(filename, content)
        self._storage.remove(filename)
        assert not self._storage.exists(filename)

    @raises(exceptions.FileNotFoundError)
    def test_read_inexistent(self):
        filename = self.gen_random_string()
        self._storage.get_content(filename)

    @raises(exceptions.FileNotFoundError)
    def test_remove_inexistent(self):
        filename = self.gen_random_string()
        self._storage.remove(filename)

    @raises(exceptions.FileNotFoundError)
    def test_get_size_inexistent(self):
        filename = self.gen_random_string()
        self._storage.get_size(filename)

    def test_stream(self):
        filename = self.gen_random_string()
        # test 7MB
        content = self.gen_random_string(7 * 1024 * 1024).encode('utf8')
        # test exists
        io = compat.StringIO(content)
        assert not self._storage.exists(filename)

        self._storage.stream_write(filename, io)
        io.close()

        assert self._storage.exists(filename)

        # test read / write
        data = compat.bytes()
        for buf in self._storage.stream_read(filename):
            data += buf
        assert content == data

        # test bytes_range only if the storage backend suppports it
        if self._storage.supports_bytes_range:
            b = random.randint(0, len(content) / 2)
            bytes_range = (b, random.randint(b + 1, len(content) - 1))
            data = compat.bytes()
            for buf in self._storage.stream_read(filename, bytes_range):
                data += buf
            expected_content = content[bytes_range[0]:bytes_range[1] + 1]
            assert data == expected_content

        # test remove
        self._storage.remove(filename)
        assert not self._storage.exists(filename)

    @raises(exceptions.FileNotFoundError)
    def test_stream_read_inexistent(self):
        filename = self.gen_random_string()
        data = compat.bytes()
        for buf in self._storage.stream_read(filename):
            data += buf

    @raises(exceptions.FileNotFoundError)
    def test_inexistent_list_directory(self):
        notexist = self.gen_random_string()
        iterator = self._storage.list_directory(notexist)
        iterator.next()

    # XXX only elliptics return StopIteration for now - though we should
    # return probably that for all
    @raises(exceptions.FileNotFoundError, StopIteration)
    def test_empty_list_directory(self):
        path = self.gen_random_string()
        content = self.gen_random_string().encode('utf8')
        self._storage.put_content(path, content)

        iterator = self._storage.list_directory(path)
        iterator.next()

    def test_list_directory(self):
        base = self.gen_random_string()
        filename1 = self.gen_random_string()
        filename2 = self.gen_random_string()
        fb1 = '%s/%s' % (base, filename1)
        fb2 = '%s/%s' % (base, filename2)
        content = self.gen_random_string()
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

    @raises(exceptions.FileNotFoundError, StopIteration)
    def test_empty_after_remove_list_directory(self):
        base = self.gen_random_string()
        filename1 = self.gen_random_string()
        filename2 = self.gen_random_string()
        fb1 = '%s/%s' % (base, filename1)
        fb2 = '%s/%s' % (base, filename2)
        content = self.gen_random_string()
        self._storage.put_content(fb1, content)
        self._storage.put_content(fb2, content)

        self._storage.remove(fb1)
        self._storage.remove(fb2)

        iterator = self._storage.list_directory(base)
        iterator.next()

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
