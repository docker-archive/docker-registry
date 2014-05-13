# -*- coding: utf-8 -*-
"""
docker_registry.drivers.file
~~~~~~~~~~~~~~~~~~~~~~~~~~

This is a simple filesystem based driver.

"""

import os
import shutil

from docker_registry.core import driver
from docker_registry.core import exceptions
from docker_registry.core import lru


class Storage(driver.Base):

    supports_bytes_range = True

    def __init__(self, path=None, config=None):
        self._root_path = path or '/tmp'

    def _init_path(self, path=None, create=False):
        path = os.path.join(self._root_path, path) if path else self._root_path
        if create is True:
            dirname = os.path.dirname(path)
            if not os.path.exists(dirname):
                os.makedirs(dirname)
        return path

    @lru.get
    def get_content(self, path):
        path = self._init_path(path)
        try:
            with open(path, mode='rb') as f:
                d = f.read()
        except Exception:
            raise exceptions.FileNotFoundError('%s is not there' % path)

        return d

    @lru.set
    def put_content(self, path, content):
        path = self._init_path(path, create=True)
        with open(path, mode='wb') as f:
            f.write(content)
        return path

    def stream_read(self, path, bytes_range=None):
        path = self._init_path(path)
        nb_bytes = 0
        total_size = 0
        with open(path, mode='rb') as f:
            if bytes_range:
                f.seek(bytes_range[0])
                total_size = bytes_range[1] - bytes_range[0] + 1
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
        path = self._init_path(path, create=True)
        with open(path, mode='wb') as f:
            try:
                while True:
                    buf = fp.read(self.buffer_size)
                    if not buf:
                        break
                    f.write(buf)
            except IOError:
                pass

    def list_directory(self, path=None):
        prefix = path + '/'
        path = self._init_path(path)
        exists = False
        try:
            for d in os.listdir(path):
                exists = True
                yield prefix + d
        except Exception:
            pass
        if not exists:
            raise exceptions.FileNotFoundError('%s is not there' % path)

    def exists(self, path):
        path = self._init_path(path)
        return os.path.exists(path)

    @lru.remove
    def remove(self, path):
        path = self._init_path(path)
        if os.path.isdir(path):
            shutil.rmtree(path)
            return
        try:
            os.remove(path)
        except OSError:
            raise exceptions.FileNotFoundError('%s is not there' % path)

    def get_size(self, path):
        path = self._init_path(path)
        try:
            return os.path.getsize(path)
        except OSError:
            raise exceptions.FileNotFoundError('%s is not there' % path)
