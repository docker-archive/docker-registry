
'''Monkeypatch S3Storage preventing parallel key stream read in unittesting.
   It is called from lib/storage/s3'''

import storage.s3
import utils


class S3Storage(storage.s3.S3Storage):
    __metaclass__ = utils.monkeypatch_class

    def stream_read(self, path):
        path = self._init_path(path)
        key = self._boto_bucket.lookup(path)
        if not key:
            raise IOError('No such key: \'{0}\''.format(path))
        while True:
            buf = key.read(self.buffer_size)
            if not buf:
                break
            yield buf
