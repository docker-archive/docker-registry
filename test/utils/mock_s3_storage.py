
'''Monkeypatch S3Storage preventing parallel key stream read in unittesting.
   It is called from lib/storage/s3'''

from docker_registry.storage import s3

from . import monkeypatch_class


class S3Storage(s3.S3Storage):
    __metaclass__ = monkeypatch_class

    def stream_read(self, path, bytes_range=None):
        path = self._init_path(path)
        nb_bytes = 0
        total_size = 0
        key = self._boto_bucket.lookup(path)
        if not key:
            raise IOError('No such key: \'{0}\''.format(path))
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
