
import os
import shutil

import cache_lru

from . import Storage


class LocalStorage(Storage):

    supports_bytes_range = True

    def __init__(self, config):
        self._config = config
        self._root_path = self._config.storage_path

    def _init_path(self, path=None, create=False):
        path = os.path.join(self._root_path, path) if path else self._root_path
        if create is True:
            dirname = os.path.dirname(path)
            if not os.path.exists(dirname):
                os.makedirs(dirname)
        return path

    @cache_lru.get
    def get_content(self, path):
        path = self._init_path(path)
        with open(path, mode='r') as f:
            return f.read()

    @cache_lru.put
    def put_content(self, path, content):
        path = self._init_path(path, create=True)
        with open(path, mode='w') as f:
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
        for d in os.listdir(path):
            exists = True
            yield prefix + d
        if exists is False:
            # Raises OSError even when the directory is empty
            # (to be consistent with S3)
            raise OSError('No such directory: \'{0}\''.format(path))

    def exists(self, path):
        path = self._init_path(path)
        return os.path.exists(path)

    @cache_lru.remove
    def remove(self, path):
        path = self._init_path(path)
        if os.path.isdir(path):
            shutil.rmtree(path)
            return
        try:
            os.remove(path)
        except OSError:
            pass

    def get_size(self, path):
        path = self._init_path(path)
        return os.path.getsize(path)
