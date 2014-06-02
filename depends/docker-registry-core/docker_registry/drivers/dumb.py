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
docker_registry.drivers.dumb
~~~~~~~~~~~~~~~~~~~~~~~~~~

This is a very dumb driver, which uses memory to store data.
It obviously won't work out of very simple tests.
Should only be used for inspiration and tests.

"""

from ..core import compat
from ..core import driver
from ..core import exceptions


class Storage(driver.Base):

    _storage = {}

    def __init__(self, path=None, config=None):
        self.supports_bytes_range = True

    def exists(self, path):
        return path in self._storage

    def get_size(self, path):
        if path not in self._storage:
            raise exceptions.FileNotFoundError('%s is not there' % path)
        return len(self._storage[path])

    def get_content(self, path):
        if path not in self._storage:
            raise exceptions.FileNotFoundError('%s is not there' % path)
        return self._storage[path]

    def put_content(self, path, content):
        self._storage[path] = content

    def remove(self, path):
        # Straight key, delete
        if path in self._storage:
            del self._storage[path]
            return
        # Directory like, get the list
        ls = []
        for k in self._storage.keys():
            if (not k == path) and k.startswith(path):
                ls.append(k)

        if not len(ls):
            raise exceptions.FileNotFoundError('%s is not there' % path)
        for item in ls:
            self.remove(item)

    def stream_read(self, path, bytes_range=None):
        if path not in self._storage:
            raise exceptions.FileNotFoundError('%s is not there' % path)

        f = self._storage[path]
        nb_bytes = 0
        total_size = 0
        if bytes_range:
            f.seek(bytes_range[0])
            total_size = bytes_range[1] - bytes_range[0] + 1
        else:
            f.seek(0)
        while True:
            buf = None
            if bytes_range:
                # Bytes Range is enabled
                buf_size = self.buffer_size
                if nb_bytes + buf_size > total_size:
                    # We make sure we don't read out of the range
                    buf_size = total_size - nb_bytes
                if buf_size > 0:
                    buf = f.read(buf_size)
                    nb_bytes += len(buf)
                else:
                    # We're at the end of the range
                    buf = ''
            else:
                buf = f.read(self.buffer_size)
            if not buf:
                break
            yield buf

    def stream_write(self, path, fp):
        # Size is mandatory
        if path not in self._storage:
            self._storage[path] = compat.StringIO()

        f = self._storage[path]
        try:
            while True:
                buf = fp.read(self.buffer_size)
                if not buf:
                    break
                f.write(buf)
        except IOError:
            pass

    def list_directory(self, path=None):
        # if path not in self._storage:
        #     raise exceptions.FileNotFoundError('%s is not there' % path)

        ls = []
        for k in self._storage.keys():
            if (not k == path) and k.startswith(path or ''):
                ls.append(k)

        if not len(ls):
            raise exceptions.FileNotFoundError('%s is not there' % path)

        return ls
