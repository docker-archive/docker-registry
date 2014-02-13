
import tempfile

import config


__all__ = ['load']


class Storage(object):

    """Storage is organized as follow:
    $ROOT/images/<image_id>/json
    $ROOT/images/<image_id>/layer
    $ROOT/repositories/<namespace>/<repository_name>/<tag_name>
    """

    # Useful if we want to change those locations later without rewriting
    # the code which uses Storage
    repositories = 'repositories'
    images = 'images'
    # Set the IO buffer to 128kB
    buffer_size = 128 * 1024
    # By default no storage plugin supports it
    supports_bytes_range = False

    #FIXME(samalba): Move all path resolver in each module (out of the base)
    def images_list_path(self, namespace, repository):
        repository_path = self.repository_path(
            namespace=namespace, repository=repository)
        return '{0}/_images_list'.format(repository_path)

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

    def image_files_path(self, image_id):
        return '{0}/{1}/_files'.format(self.images, image_id)

    def image_diff_path(self, image_id):
        return '{0}/{1}/_diff'.format(self.images, image_id)

    def repository_path(self, namespace, repository):
        return '{0}/{1}/{2}'.format(
            self.repositories, namespace, repository)

    def tag_path(self, namespace, repository, tagname=None):
        repository_path = self.repository_path(
            namespace=namespace, repository=repository)
        if not tagname:
            return repository_path
        return '{0}/tag_{1}'.format(repository_path, tagname)

    def repository_json_path(self, namespace, repository):
        repository_path = self.repository_path(
            namespace=namespace, repository=repository)
        return '{0}/json'.format(repository_path)

    def repository_tag_json_path(self, namespace, repository, tag):
        repository_path = self.repository_path(
            namespace=namespace, repository=repository)
        return '{0}/tag{1}_json'.format(repository_path, tag)

    def index_images_path(self, namespace, repository):
        repository_path = self.repository_path(
            namespace=namespace, repository=repository)
        return '{0}/_index_images'.format(repository_path)

    def private_flag_path(self, namespace, repository):
        repository_path = self.repository_path(
            namespace=namespace, repository=repository)
        return '{0}/_private'.format(repository_path)

    def is_private(self, namespace, repository):
        return self.exists(self.private_flag_path(namespace, repository))

    def get_content(self, path):
        raise NotImplementedError

    def put_content(self, path, content):
        raise NotImplementedError

    def stream_read(self, path, bytes_range=None):
        raise NotImplementedError

    def stream_write(self, path, fp):
        raise NotImplementedError

    def list_directory(self, path=None):
        raise NotImplementedError

    def exists(self, path):
        raise NotImplementedError

    def remove(self, path):
        raise NotImplementedError

    def get_size(self, path):
        raise NotImplementedError


def temp_store_handler():
    tmpf = tempfile.TemporaryFile()

    def fn(buf):
        tmpf.write(buf)

    return tmpf, fn


from local import LocalStorage


_storage = {}


def load(kind=None):
    """Returns the right storage class according to the configuration."""
    global _storage
    cfg = config.load()
    if not kind:
        kind = cfg.storage.lower()
    if kind in _storage:
        return _storage[kind]
    if kind == 's3':
        import s3
        store = s3.S3Storage(cfg)
    elif kind == 'swift':
        import swift
        store = swift.SwiftStorage(cfg)
    elif kind == 'local':
        store = LocalStorage(cfg)
    elif kind == 'glance':
        import glance
        store = glance.GlanceStorage(cfg)
    elif kind == 'elliptics':
        import ellipticsbackend
        store = ellipticsbackend.EllipticsStorage(cfg)
    elif kind == 'gcs':
        import gcs
        store = gcs.GSStorage(cfg)
    else:
        raise ValueError('Not supported storage \'{0}\''.format(kind))
    _storage[kind] = store
    return store
