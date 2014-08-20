# -*- coding: utf-8 -*-

'''Monkeypatch s3 Storage preventing parallel key stream read in unittesting.
   It is called from lib/storage/s3'''

import six

from docker_registry.core import exceptions
import docker_registry.drivers.s3 as s3
from docker_registry.testing import utils


@six.add_metaclass(utils.monkeypatch_class)
class Storage(s3.Storage):

    # def stream_read(self, path, bytes_range=None):
    #     path = self._init_path(path)
    #     headers = None
    #     if bytes_range:
    #         headers = {'Range': 'bytes={0}-{1}'.format(*bytes_range)}
    #     key = self._boto_bucket.lookup(path, headers=headers)
    #     if not key:
    #         raise exceptions.FileNotFoundError('%s is not there' % path)
    #     while True:
    #         buf = key.read(self.buffer_size)
    #         if not buf:
    #             break
    #         yield buf

    def stream_read(self, path, bytes_range=None):
        path = self._init_path(path)
        nb_bytes = 0
        total_size = 0
        key = self._boto_bucket.lookup(path)
        if not key:
            raise exceptions.FileNotFoundError('%s is not there' % path)
        if bytes_range:
            key._last_position = bytes_range[0]
            total_size = bytes_range[1] - bytes_range[0] + 1
        while True:
            if bytes_range:
                # Bytes Range is enabled
                buf_size = self.buffer_size
                if nb_bytes + buf_size > total_size:
                    # We make sure we don't read out of the range
                    buf_size = total_size - nb_bytes
                if buf_size > 0:
                    buf = key.read(buf_size)
                    nb_bytes += len(buf)
                else:
                    # We're at the end of the range
                    buf = ''
            else:
                buf = key.read(self.buffer_size)
            if not buf:
                break
            yield buf
