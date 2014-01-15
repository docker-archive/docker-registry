
import gevent.monkey
gevent.monkey.patch_all()

import cStringIO as StringIO
import logging

import boto.s3.connection
import boto.s3.key

import cache_lru

from boto_base import BotoStorage


logger = logging.getLogger(__name__)


class S3Storage(BotoStorage):

    def __init__(self, config):
        BotoStorage.__init__(self, config)

    def makeConnection(self):
        return boto.s3.connection.S3Connection(
            self._config.s3_access_key,
            self._config.s3_secret_key,
            is_secure=(self._config.s3_secure is True))

    def makeKey(self, path):
        return boto.s3.key.Key(self._boto_bucket, path)

    @cache_lru.put
    def put_content(self, path, content):
        path = self._init_path(path)
        key = self.makeKey(path)
        key.set_contents_from_string(
            content, encrypt_key=(self._config.s3_encrypt is True))
        return path

    def stream_write(self, path, fp):
        # Minimum size of upload part size on S3 is 5MB
        buffer_size = 5 * 1024 * 1024
        if self.buffer_size > buffer_size:
            buffer_size = self.buffer_size
        path = self._init_path(path)
        mp = self._boto_bucket.initiate_multipart_upload(
            path, encrypt_key=(self._config.s3_encrypt is True))
        num_part = 1
        try:
            while True:
                buf = fp.read(buffer_size)
                if not buf:
                    break
                io = StringIO.StringIO(buf)
                mp.upload_part_from_file(io, num_part)
                num_part += 1
                io.close()
        except IOError:
            pass
        mp.complete_upload()
