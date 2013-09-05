
import cStringIO as StringIO
import os

import boto.s3.connection
import boto.s3.key

from . import Storage


class S3Storage(Storage):

    def __init__(self, config):
        self._config = config
        self._s3_conn = \
            boto.s3.connection.S3Connection(self._config.s3_access_key,
                                            self._config.s3_secret_key,
                                            is_secure=False)
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

    def get_content(self, path):
        path = self._init_path(path)
        key = boto.s3.key.Key(self._s3_bucket, path)
        if not key.exists():
            raise IOError('No such key: \'{0}\''.format(path))
        return key.get_contents_as_string()

    def put_content(self, path, content):
        path = self._init_path(path)
        key = boto.s3.key.Key(self._s3_bucket, path)
        key.set_contents_from_string(content)
        return path

    def stream_read(self, path):
        path = self._init_path(path)
        key = boto.s3.key.Key(self._s3_bucket, path)
        if not key.exists():
            raise IOError('No such key: \'{0}\''.format(path))
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
        mp = self._s3_bucket.initiate_multipart_upload(path)
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
