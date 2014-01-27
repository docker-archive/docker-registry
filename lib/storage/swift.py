
import cache_lru
import swiftclient

from . import Storage


class SwiftStorage(Storage):

    def __init__(self, config):
        self._swift_connection = self._create_swift_connection(config)
        self._swift_container = config.swift_container
        self._root_path = config.get('storage_path', '/')

    def _create_swift_connection(self, config):
        return swiftclient.client.Connection(
            authurl=config.get('swift_authurl'),
            user=config.get('swift_user'),
            key=config.get('swift_password'),
            auth_version=config.get('swift_auth_version', 2),
            os_options={
                'tenant_name': config.get('swift_tenant_name'),
                'region_name': config.get('swift_region_name')
            })

    def _init_path(self, path=None):
        path = self._root_path + '/' + path if path else self._root_path
        # Openstack does not like paths starting with '/'
        if path and path.startswith('/'):
            path = path[1:]
        return path

    @cache_lru.get
    def get_content(self, path, chunk_size=None):
        path = self._init_path(path)
        try:
            _, obj = self._swift_connection.get_object(
                self._swift_container,
                path,
                resp_chunk_size=chunk_size)
            return obj
        except Exception:
            raise IOError("Could not get content: {}".format(path))

    @cache_lru.put
    def put_content(self, path, content, chunk=None):
        path = self._init_path(path)
        try:
            self._swift_connection.put_object(self._swift_container,
                                              path,
                                              content,
                                              chunk_size=chunk)
            return path
        except Exception:
            raise IOError("Could not put content: {}".format(path))

    def stream_read(self, path, bytes_range=None):
        try:
            for buf in self.get_content(path, self.buffer_size):
                yield buf
        except Exception:
            raise OSError(
                "Could not read content from stream: {}".format(path))

    def stream_write(self, path, fp):
        self.put_content(path, fp, self.buffer_size)

    def list_directory(self, path=None):
        try:
            path = self._init_path(path)
            if path and not path.endswith('/'):
                path += '/'
            _, directory = self._swift_connection.get_container(
                container=self._swift_container,
                path=path)
            if not directory:
                raise
            for inode in directory:
                # trim extra trailing slashes
                if inode['name'].endswith('/'):
                    inode['name'] = inode['name'][:-1]
                yield inode['name'].replace(self._root_path[1:] + '/', '', 1)
        except Exception:
            raise OSError("No such directory: {}".format(path))

    def exists(self, path):
        try:
            self.get_content(path)
            return True
        except Exception:
            return False

    @cache_lru.remove
    def remove(self, path):
        path = self._init_path(path)
        try:
            self._swift_connection.delete_object(self._swift_container, path)
        except Exception:
            pass

    def get_size(self, path):
        try:
            return len(self.get_content(path))
        except Exception:
            raise OSError("Could not get file size: {}".format(path))
