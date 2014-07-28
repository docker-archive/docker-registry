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

"""
docker_registry.core.boto
~~~~~~~~~~~~~~~~~~~~~~~~~~

Might be useful for
 * Amazon Simple Storage Service (S3)
 * Google Cloud Storage
 * Amazon Glacier
 * Amazon Elastic Block Store (EBS)

"""

import gevent.monkey
gevent.monkey.patch_all()

import copy
import logging
import math
import os
import tempfile

from . import driver
from . import lru

from .exceptions import FileNotFoundError

logger = logging.getLogger(__name__)


class ParallelKey(object):

    """This class implements parallel transfer on a key to improve speed."""

    CONCURRENCY = 5

    def __init__(self, key):
        logger.info('ParallelKey: {0}; size={1}'.format(key, key.size))
        self._boto_key = key
        self._cursor = 0
        self._max_completed_byte = 0
        self._max_completed_index = 0
        self._tmpfile = tempfile.NamedTemporaryFile(mode='rb')
        self._completed = [0] * self.CONCURRENCY
        self._spawn_jobs()

    def __del__(self):
        self._tmpfile.close()

    def _generate_bytes_ranges(self, num_parts):
        size = self._boto_key.size
        chunk_size = int(math.ceil(1.0 * size / num_parts))
        for i in range(num_parts):
            yield (i, chunk_size * i, min(chunk_size * (i + 1) - 1, size - 1))

    def _fetch_part(self, fname, index, min_cur, max_cur):
        boto_key = copy.copy(self._boto_key)
        with open(fname, 'wb') as f:
            f.seek(min_cur)
            brange = 'bytes={0}-{1}'.format(min_cur, max_cur)
            boto_key.get_contents_to_file(f, headers={'Range': brange})
            boto_key.close()
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
                percent = round(
                    (100.0 * self._cursor) / self._boto_key.size, 1)
                logger.info('ParallelKey: {0}; buffering complete at {1}% of '
                            'the total transfer; now serving straight from '
                            'the tempfile'.format(self._boto_key, percent))

    def read(self, size):
        if self._cursor >= self._boto_key.size:
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
                           self._boto_key, self._cursor, self._boto_key.size))
            logging.error(message)
            raise RuntimeError(message)
        return buf


class Base(driver.Base):

    supports_bytes_range = True

    def __init__(self, path=None, config=None):
        self._config = config
        self._root_path = path or '/test'
        self._boto_conn = self.makeConnection()
        self._boto_bucket = self._boto_conn.get_bucket(
            self._config.boto_bucket)
        logger.info("Boto based storage initialized")

    def _build_connection_params(self):
        kwargs = {'is_secure': (self._config.s3_secure is True)}
        config_args = [
            'host', 'port', 'debug',
            'proxy', 'proxy_port',
            'proxy_user', 'proxy_pass'
        ]
        for arg in config_args:
            confkey = 'boto_' + arg
            if getattr(self._config, confkey, None) is not None:
                kwargs[arg] = getattr(self._config, confkey)
        return kwargs

    def _debug_key(self, key):
        """Used for debugging only."""
        orig_meth = key.bucket.connection.make_request

        def new_meth(*args, **kwargs):
            print('#' * 16)
            print(args)
            print(kwargs)
            print('#' * 16)
            return orig_meth(*args, **kwargs)
        key.bucket.connection.make_request = new_meth

    def _init_path(self, path=None):
        path = os.path.join(self._root_path, path) if path else self._root_path
        if path and path[0] == '/':
            return path[1:]
        return path

    def stream_read(self, path, bytes_range=None):
        path = self._init_path(path)
        headers = None
        if bytes_range:
            headers = {'Range': 'bytes={0}-{1}'.format(*bytes_range)}
        key = self._boto_bucket.lookup(path, headers=headers)
        if not key:
            raise FileNotFoundError('%s is not there' % path)
        if not bytes_range and key.size > 1024 * 1024:
            # Use the parallel key only if the key size is > 1MB
            # And if bytes_range is not enabled (since ParallelKey is already
            # using bytes range)
            key = ParallelKey(key)
        while True:
            buf = key.read(self.buffer_size)
            if not buf:
                break
            yield buf

    def list_directory(self, path=None):
        path = self._init_path(path)
        if not path.endswith('/'):
            path += '/'
        ln = 0
        if self._root_path != '/':
            ln = len(self._root_path)
        exists = False
        for key in self._boto_bucket.list(prefix=path, delimiter='/'):
            if '%s/' % key.name == path:
                continue
            exists = True
            name = key.name
            if name.endswith('/'):
                yield name[ln:-1]
            else:
                yield name[ln:]
        if not exists:
            raise FileNotFoundError('%s is not there' % path)

    def get_size(self, path):
        path = self._init_path(path)
        # Lookup does a HEAD HTTP Request on the object
        key = self._boto_bucket.lookup(path)
        if not key:
            raise FileNotFoundError('%s is not there' % path)
        return key.size

    @lru.get
    def get_content(self, path):
        path = self._init_path(path)
        key = self.makeKey(path)
        if not key.exists():
            raise FileNotFoundError('%s is not there' % path)
        return key.get_contents_as_string()

    def exists(self, path):
        path = self._init_path(path)
        key = self.makeKey(path)
        return key.exists()

    @lru.remove
    def remove(self, path):
        path = self._init_path(path)
        key = self.makeKey(path)
        if key.exists():
            # It's a file
            key.delete()
            return
        # We assume it's a directory
        if not path.endswith('/'):
            path += '/'
        exists = False
        for key in self._boto_bucket.list(prefix=path, delimiter='/'):
            if '%s/' % key.name == path:
                continue
            exists = True
            key.delete()
        if not exists:
            raise FileNotFoundError('%s is not there' % path)
