import StringIO
import sys

from docker_registry import storage

import test_local_storage

# noqa is issued to allow imports do their monkeypatching as side effect
import utils.mock_boto_s3                     # noqa
from utils.mock_s3_storage import S3Storage   # noqa

StringIO_read = StringIO.StringIO.read


class StringIOWithError(StringIO.StringIO):
    '''Throw IOError after reaching EOF.'''

    def read(self, size):
        if self.pos == self.len:
            raise IOError('Reading beyond EOF')
        return StringIO_read(self, size)


class TestS3Storage(test_local_storage.TestLocalStorage):
    '''Extra tests for coverage completion.'''

    def setUp(self):
        self._storage = storage.load('s3')

    def tearDown(self):
        self._storage._boto_bucket.delete()

    def test_list_bucket(self):
        # Add a couple of bucket keys
        filename1 = self.gen_random_string()
        filename2 = self.gen_random_string()
        content = self.gen_random_string()
        self._storage.put_content(filename1, content)
        # Check bucket key is stored in normalized form
        self._storage.put_content(filename2 + '/', content)
        # Check both keys are in the bucket
        self.assertEqual(sorted([filename1, filename2]),
                         sorted(list(self._storage.list_directory())))
        # Check listing bucket raises exception after removing keys
        self._storage.remove(filename1)
        self._storage.remove(filename2)
        self.assertRaises(OSError, next, self._storage.list_directory())

    def test_stream_write(self):
        # Check stream write with buffer bigger than default 5MB
        self._storage.buffer_size = 7 * 1024 * 1024
        filename = self.gen_random_string()
        # Test 8MB
        content = self.gen_random_string(8 * 1024 * 1024)
        io = StringIOWithError(content)
        self.assertFalse(self._storage.exists(filename))
        self._storage.stream_write(filename, io)
        self.assertTrue(self._storage.exists(filename))
        # Test that EOFed io string throws IOError on lib/storage/s3
        self._storage.stream_write(filename, io)
        # Cleanup
        io.close()
        self._storage.remove(filename)
        self._storage.buffer_size = 5 * 1024 * 1024
        self.assertFalse(self._storage.exists(filename))

    def test_init_path(self):
        # s3 storage _init_path result keys are relative (no / at start)
        root_path = self._storage._root_path
        if root_path.startswith('/'):
            self._storage._root_path = root_path[1:]
            self.assertFalse(self._storage._init_path().startswith('/'))
            self._storage._root_path = root_path

    def test_debug_key(self):
        # Create a valid s3 key object to debug
        filename = self.gen_random_string()
        content = self.gen_random_string()
        self._storage.put_content(filename, content)

        # Get filename key path as stored
        key_path = self._storage._init_path(filename)
        key = self._storage._boto_bucket.lookup(key_path)
        self._storage._debug_key(key)

        # Capture debugged output
        saved_stdout = sys.stdout
        output = StringIO.StringIO()
        sys.stdout = output

        # As key is mocked for unittest purposes, we call make_request directly
        dummy = '{}\n{}\n{}\n{}\n'.format(
            '#' * 16, ('d', 1), {'v': 2}, '#' * 16)
        result = self._storage._boto_bucket.connection.make_request(
            'd', 1, v=2)
        self.assertEqual(output.getvalue(), dummy)
        self.assertEqual(result, 'request result')

        sys.stdout = saved_stdout

        # We don't call self._storage.remove(filename) here to ensure tearDown
        # cleanup properly and that other tests keep running as expected.
