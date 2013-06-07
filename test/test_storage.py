
from cStringIO import StringIO

import base
import storage


class TestLocalStorage(base.TestCase):

    def setUp(self):
        self._storage = storage.load('local')

    def test_simple(self):
        filename = self.gen_random_string()
        content = self.gen_random_string()
        # test exists
        self.assertFalse(self._storage.exists(filename))
        self._storage.put_content(filename, content)
        self.assertTrue(self._storage.exists(filename))
        # test read / write
        ret = self._storage.get_content(filename)
        self.assertEqual(ret, content)
        # test size
        ret = self._storage.get_size(filename)
        self.assertEqual(ret, len(content))
        # test remove
        self._storage.remove(filename)
        self.assertFalse(self._storage.exists(filename))

    def test_stream(self):
        filename = self.gen_random_string()
        # test 7MB
        content = self.gen_random_string(7 * 1024 * 1024)
        # test exists
        io = StringIO(content)
        self.assertFalse(self._storage.exists(filename))
        self._storage.stream_write(filename, io)
        io.close()
        self.assertTrue(self._storage.exists(filename))
        # test read / write
        data = ''
        for buf in self._storage.stream_read(filename):
            data += buf
        self.assertEqual(content, data)
        # test remove
        self._storage.remove(filename)
        self.assertFalse(self._storage.exists(filename))

    def test_errors(self):
        notexist = self.gen_random_string()
        self.assertRaises(IOError, self._storage.get_content, notexist)
        iterator = self._storage.list_directory(notexist)
        self.assertRaises(OSError, next, iterator)
        self.assertRaises(OSError, self._storage.get_size, notexist)


class TestS3Storage(TestLocalStorage):

    def setUp(self):
        self._storage = storage.load('s3')
