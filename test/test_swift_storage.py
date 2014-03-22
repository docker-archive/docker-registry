
import StringIO

# noqa is issued to allow imports do their monkeypatching as side effect
from utils.mock_swift_storage import Connection   # noqa

from docker_registry import storage

import test_local_storage


class TestSwiftStorage(test_local_storage.TestLocalStorage):

    def setUp(self):
        self._storage = storage.load('swift')
        self._storage._swift_connection.put_container(
            self._storage._swift_container
        )

    def tearDown(self):
        self._storage._swift_connection.delete_container(
            self._storage._swift_container
        )

    def test_list_container(self):
        # Add a couple of container keys
        filename1 = self.gen_random_string()
        filename2 = self.gen_random_string()
        content = self.gen_random_string()
        self._storage.put_content(filename1, content)
        self._storage.put_content(filename2, content)
        # Check both objects are in the container
        self.assertEqual(sorted([filename1, filename2]),
                         sorted(list(self._storage.list_directory())))
        # Check listing container raises exception after removing objects
        self._storage.remove(filename1)
        self._storage.remove(filename2)
        self.assertRaises(OSError, next, self._storage.list_directory())

    def test_stream_write(self):
        # Check stream write with buffer bigger than default 5MB
        self._storage.buffer_size = 7 * 1024 * 1024
        filename = self.gen_random_string()
        # Test 8MB
        content = self.gen_random_string(8 * 1024 * 1024)
        io = StringIO.StringIO(content)
        self.assertFalse(self._storage.exists(filename))
        self._storage.stream_write(filename, io)
        self.assertTrue(self._storage.exists(filename))
        # Test that EOFed io string throws IOError on lib/storage/swift
        self._storage.stream_write(filename, io)
        # Cleanup
        io.close()
        self._storage.remove(filename)
        self._storage.buffer_size = 5 * 1024 * 1024
        self.assertFalse(self._storage.exists(filename))

    def test_init_path(self):
        # swift storage _init_path result keys are relative (no / at start)
        root_path = self._storage._root_path
        if root_path.startswith('/'):
            self._storage._root_path = root_path[1:]
            self.assertFalse(self._storage._init_path().startswith('/'))
            self._storage._root_path = root_path
