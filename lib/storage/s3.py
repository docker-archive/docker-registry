
import gevent.monkey
gevent.monkey.patch_all()

import copy
import cStringIO as StringIO
import logging
import math
import os
import tempfile

import boto.s3.connection
import boto.s3.key

import cache

from . import Storage


logger = logging.getLogger(__name__)


class ParallelKey(object):

    """This class implements parallel transfer on a key to improve speed."""

    CONCURRENCY = 20

    def __init__(self, key):
        logger.info('ParallelKey: {0}; size={1}'.format(key, key.size))
        self._s3_key = key
        self._cursor = 0
        self._max_completed_byte = 0
        self._max_completed_index = 0
        self._tmpfile = tempfile.NamedTemporaryFile(mode='rb')
        self._completed = [0] * self.CONCURRENCY
        self._spawn_jobs()

    def __del__(self):
        self._tmpfile.close()

    def _generate_bytes_ranges(self, num_parts):
        size = self._s3_key.size
        chunk_size = int(math.ceil(1.0 * size / num_parts))
        for i in range(num_parts):
            yield (i, chunk_size * i, min(chunk_size * (i + 1) - 1, size - 1))

    def _fetch_part(self, fname, index, min_cur, max_cur):
        s3_key = copy.copy(self._s3_key)
        with open(fname, 'wb') as f:
            f.seek(min_cur)
            brange = 'bytes={0}-{1}'.format(min_cur, max_cur)
            s3_key.get_contents_to_file(f, headers={'Range': brange})
            s3_key.close()
        self._completed[index] = (index, max_cur)
        self._refresh_max_completed_byte()

    def _spawn_jobs(self):
        bytes_ranges = self._generate_bytes_ranges(self.CONCURRENCY)
        for i, min_cur, max_cur in bytes_ranges:
            gevent.spawn(self._fetch_part, self._tmpfile.name,
                         i, min_cur, max_cur)

    def _refresh_max_completed_byte(self):
        for v in self._completed[self._max_completed_index:]:
            if v == 0:
                return
            self._max_completed_index = v[0]
            self._max_completed_byte = v[1]
            if self._max_completed_index >= len(self._completed) - 1:
                percent = round((100.0 * self._cursor) / self._s3_key.size, 1)
                logger.info('ParallelKey: {0}; buffering complete at {1}% of '
                            'the total transfer; now serving straight from '
                            'the tempfile'.format(self._s3_key, percent))

    def read(self, size):
        if self._cursor >= self._s3_key.size:
            # Read completed
            return ''
        sz = size
        if self._max_completed_index < len(self._completed) - 1:
            # Not all data arrived yet
            if self._cursor + size > self._max_completed_byte:
                while self._cursor >= self._max_completed_byte:
                    # We're waiting for more data to arrive
                    gevent.sleep(0.2)
            if self._cursor + sz > self._max_completed_byte:
                sz = self._max_completed_byte - self._cursor
        # Use a low-level read to avoid any buffering (makes sure we don't
        # read more than `sz' bytes).
        buf = os.read(self._tmpfile.file.fileno(), sz)
        self._cursor += len(buf)
        if not buf:
            message = ('ParallelKey: {0}; got en empty read on the buffer! '
                       'cursor={1}, size={2}; Transfer interrupted.'.format(
                           self._s3_key, self._cursor, self._s3_key.size))
            logging.error(message)
            raise RuntimeError(message)
        return buf


class S3Storage(Storage):

    def __init__(self, config):
        self._config = config
        self._s3_conn = boto.s3.connection.S3Connection(
            self._config.s3_access_key,
            self._config.s3_secret_key,
            is_secure=(self._config.s3_secure is True))
        self._s3_bucket = self._s3_conn.get_bucket(self._config.s3_bucket)
        self._root_path = self._config.storage_path

    def _debug_key(self, key):
        """Used for debugging only."""
        orig_meth = key.bucket.connection.make_request

        def new_meth(*args, **kwargs):
            print '#' * 16
            print args
            print kwargs
            print '#' * 16
            return orig_meth(*args, **kwargs)
        key.bucket.connection.make_request = new_meth

    def _init_path(self, path=None):
        path = os.path.join(self._root_path, path) if path else self._root_path
        if path and path[0] == '/':
            return path[1:]
        return path

    @cache.get
    def get_content(self, path):
        path = self._init_path(path)
        key = boto.s3.key.Key(self._s3_bucket, path)
        if not key.exists():
            raise IOError('No such key: \'{0}\''.format(path))
        return key.get_contents_as_string()

    @cache.put
    def put_content(self, path, content):
        path = self._init_path(path)
        key = boto.s3.key.Key(self._s3_bucket, path)
        key.set_contents_from_string(
            content, encrypt_key=(self._config.s3_encrypt is True))
        return path

    def stream_read(self, path):
        path = self._init_path(path)
        key = self._s3_bucket.lookup(path)
        if not key:
            raise IOError('No such key: \'{0}\''.format(path))
        if key.size > 1024 * 1024:
            # Use the parallel key only if the key size is > 1MB
            key = ParallelKey(key)
        while True:
            buf = key.read(self.buffer_size)
            if not buf:
                break
            yield buf

    def stream_write(self, path, fp):
        # Minimum size of upload part size on S3 is 5MB
        buffer_size = 5 * 1024 * 1024
        if self.buffer_size > buffer_size:
            buffer_size = self.buffer_size
        path = self._init_path(path)
        mp = self._s3_bucket.initiate_multipart_upload(
            path, encrypt_key=(self._config.s3_encrypt is True))
        num_part = 1
        while True:
            try:
                buf = fp.read(buffer_size)
                if not buf:
                    break
                io = StringIO.StringIO(buf)
                mp.upload_part_from_file(io, num_part)
                num_part += 1
                io.close()
            except IOError:
                break
        mp.complete_upload()

    def list_directory(self, path=None):
        path = self._init_path(path)
        if not path.endswith('/'):
            path += '/'
        ln = 0
        if self._root_path != '/':
            ln = len(self._root_path)
        exists = False
        for key in self._s3_bucket.list(prefix=path, delimiter='/'):
            exists = True
            name = key.name
            if name.endswith('/'):
                yield name[ln:-1]
            else:
                yield name[ln:]
        if exists is False:
            # In order to be compliant with the LocalStorage API. Even though
            # S3 does not have a concept of folders.
            raise OSError('No such directory: \'{0}\''.format(path))

    def exists(self, path):
        path = self._init_path(path)
        key = boto.s3.key.Key(self._s3_bucket, path)
        return key.exists()

    @cache.remove
    def remove(self, path):
        path = self._init_path(path)
        key = boto.s3.key.Key(self._s3_bucket, path)
        if key.exists():
            # It's a file
            key.delete()
            return
        # We assume it's a directory
        if not path.endswith('/'):
            path += '/'
        for key in self._s3_bucket.list(prefix=path, delimiter='/'):
            key.delete()

    def get_size(self, path):
        path = self._init_path(path)
        # Lookup does a HEAD HTTP Request on the object
        key = self._s3_bucket.lookup(path)
        if not key:
            raise OSError('No such key: \'{0}\''.format(path))
        return key.size
