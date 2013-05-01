
import os
from cStringIO import StringIO

import boto.s3.connection
import boto.s3.key

import config


class Storage(object):

    """ Storage is organized as follow:
    $ROOT/images/<image_id>/json
    $ROOT/images/<image_id>/layer
    $ROOT/repositories/<namespace>/<repository_name>/<tag_name>
    """

    # Useful if we want to change those locations later without rewriting
    # the code which uses Storage
    repositories = 'repositories'
    images = 'images'
    buffer_size = 4096

    def images_list_path(self, namespace, repository):
        return '{0}/{1}/{2}/_images_list'.format(self.repositories, namespace,
            repository)

    def image_json_path(self, image_id):
        return '{0}/{1}/json'.format(self.images, image_id)

    def image_mark_path(self, image_id):
        return '{0}/{1}/_inprogress'.format(self.images, image_id)

    def image_checksum_path(self, image_id):
        return '{0}/{1}/_checksum'.format(self.images, image_id)

    def image_layer_path(self, image_id):
        return '{0}/{1}/layer'.format(self.images, image_id)

    def image_ancestry_path(self, image_id):
        return '{0}/{1}/ancestry'.format(self.images, image_id)

    def tag_path(self, namespace, repository, tagname=None):
        if not tagname:
            return '{0}/{1}/{2}'.format(self.repositories, namespace,
                    repository)
        return '{0}/{1}/{2}/tag_{3}'.format(self.repositories, namespace,
            repository, tagname)

    def get_content(self, path):
        raise NotImplemented

    def put_content(self, path, content):
        raise NotImplemented

    def stream_read(self, path):
        raise NotImplemented

    def stream_write(self, path, fp):
        raise NotImplemented

    def list_directory(self, path=None):
        raise NotImplemented

    def exists(self, path):
        raise NotImplemented

    def remove(self, path):
        raise NotImplemented


class LocalStorage(Storage):

    def __init__(self):
        self._config = config.load()
        self._root_path = self._config.storage_path

    def _init_path(self, path=None, create=False):
        path = os.path.join(self._root_path, path) if path else self._root_path
        if create is True:
            dirname = os.path.dirname(path)
            if not os.path.exists(dirname):
                os.makedirs(dirname)
        return path

    def get_content(self, path):
        path = self._init_path(path)
        with open(path, mode='r') as f:
            return f.read()

    def put_content(self, path, content):
        path = self._init_path(path, create=True)
        with open(path, mode='w') as f:
            f.write(content)
        return path

    def stream_read(self, path):
        path = self._init_path(path)
        with open(path, mode='rb') as f:
            while True:
                buf = f.read(self.buffer_size)
                if not buf:
                    break
                yield buf

    def stream_write(self, path, fp):
        # Size is mandatory
        path = self._init_path(path, create=True)
        with open(path, mode='wb') as f:
            while True:
                try:
                    buf = fp.read(self.buffer_size)
                    if not buf:
                        break
                    f.write(buf)
                except IOError:
                    break

    def list_directory(self, path=None):
        path = self._init_path(path)
        prefix = path[len(self._root_path) + 1:] + '/'
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

    def remove(self, path):
        path = self._init_path(path)
        if os.path.isdir(path):
            os.rmdir(path)
            return
        os.remove(path)


class S3Storage(Storage):

    def __init__(self):
        self._config = config.load()
        self._s3_conn = boto.s3.connection.S3Connection(
                self._config.s3_access_key,
                self._config.s3_secret_key,
                is_secure=False)
        self._s3_bucket = self._s3_conn.get_bucket(self._config.s3_bucket)
        self._root_path = self._config.storage_path

    def _debug_key(self, key):
        """ Used for debugging only """
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
                io = StringIO(buf)
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
        if not key.exists():
            raise OSError('No such key: \'{0}\''.format(path))
        key.delete()


_storage = {}
def load(kind=None):
    """ Returns the right storage class according to the configuration """
    global _storage
    if not kind:
        kind = config.load().storage.lower()
    if kind in _storage:
        return _storage[kind]
    if kind == 's3':
        store = S3Storage()
    elif kind == 'local':
        store = LocalStorage()
    else:
        raise ValueError('Not supported storage \'{0}\''.format(kind))
    _storage[kind] = store
    return store
