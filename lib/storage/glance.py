
import os

import flask
import glanceclient
from keystoneclient.v2_0 import client as keystoneclient

import signals

from . import Storage
from .local import LocalStorage
from .s3 import S3Storage
from .swift import SwiftStorage


class GlanceStorage(object):

    """This class is a dispatcher, it forwards methods accessing repositories
       to the alternate storage defined in the config and it forwards methods
       accessing images to the GlanceStorageLayers class below.
    """

    def __init__(self, config):
        self._config = config
        self._storage_layers = GlanceStorageLayers(config)
        kind = config.get('storage_alternate', 'local')
        self._storage_base = Storage()
        if kind == 's3':
            self._storage_tags = S3Storage(config)
        elif kind == 'local':
            self._storage_tags = LocalStorage(config)
        elif kind == 'swift':
            self._storage_tags = SwiftStorage(config)
        else:
            raise ValueError('Not supported storage \'{0}\''.format(kind))

    def _resolve_class_path(self, method_name, *args, **kwargs):
        path = ''
        if 'path' in kwargs:
            path = kwargs['path']
        elif len(args) > 0 and isinstance(args[0], basestring):
            path = args[0]
        if path.startswith(Storage.images):
            # The metadata is to huge as it can be
            # uploaded to glance (broken pipe).
            # Lets store it in the tags repository
            if path.endswith("_files"):
                obj = self._storage_tags
            else:
                obj = self._storage_layers
        elif path.startswith(Storage.repositories):
            obj = self._storage_tags
        else:
            obj = self._storage_layers
        if not hasattr(obj, method_name):
            return
        return getattr(obj, method_name)

    def __getattr__(self, name):
        def dispatcher(*args, **kwargs):
            attr = self._resolve_class_path(name, *args, **kwargs)
            if not attr:
                raise ValueError('Cannot dispath method '
                                 '"{0}" args: {1}, {2}'.format(name,
                                                               args,
                                                               kwargs))
            if callable(attr):
                return attr(*args, **kwargs)
            return attr
        return dispatcher


class GlanceStorageLayers(Storage):

    """This class stores the image layers into OpenStack Glance.
       However tags are still stored on other filesystem-like stores.
    """

    disk_format = 'raw'
    container_format = 'docker'

    def __init__(self, config):
        self._config = config
        # Hooks the tag changes
        signals.tag_created.connect(self._handler_tag_created)
        signals.tag_deleted.connect(self._handler_tag_deleted)

    def _get_auth_token(self):
        args = {}
        for arg in ['username', 'password', 'tenant_name', 'auth_url']:
            env_name = 'OS_{0}'.format(arg.upper())
            if env_name not in os.environ:
                raise ValueError('Cannot find env var "{0}"'.format(env_name))
            args[arg] = os.environ[env_name]
        keystone = keystoneclient.Client(**args)
        return keystone.auth_token

    def _get_endpoint(self):
        if 'OS_GLANCE_URL' not in os.environ:
            raise ValueError('Cannot find env var "OS_GLANCE_URL"')
        return os.environ['OS_GLANCE_URL']

    def _create_glance_client(self):
        token = flask.request.headers.get('X-Meta-Auth-Token')
        endpoint = flask.request.headers.get('X-Meta-Glance-Endpoint')
        if not token:
            token = self._get_auth_token()
        if not endpoint:
            endpoint = self._get_endpoint()
        return glanceclient.Client('1', endpoint=endpoint, token=token)

    def _init_path(self, path, create=True):
        """This resolve a standard Docker Registry path
           and returns: glance_image obj, property_name
           If property name is None, we want to reach the image_data
        """
        parts = path.split('/')
        if len(parts) != 3 or parts[0] != self.images:
            raise ValueError('Invalid path: {0}'.format(path))
        image_id = parts[1]
        filename = parts[2]
        glance = self._create_glance_client()
        image = self._find_image_by_id(glance, image_id)
        if not image and create is True:
            if 'X-Meta-Glance-Image-Id' in flask.request.headers:
                try:
                    i = glance.images.get(
                        flask.request.headers['X-Meta-Glance-Image-Id'])
                    if i.status == 'queued':
                        # We allow taking existing images only when queued
                        image = i
                        image.update(properties={'id': image_id},
                                     purge_props=False)
                except Exception:
                    pass
            if not image:
                image = glance.images.create(
                    disk_format=self.disk_format,
                    container_format=self.container_format,
                    properties={'id': image_id})
            try:
                image.update(is_public=True, purge_props=False)
            except Exception:
                pass
        propname = 'meta_{0}'.format(filename)
        if filename == 'layer':
            propname = None
        return image, propname

    def _find_image_by_id(self, glance, image_id):
        filters = {
            'disk_format': self.disk_format,
            'container_format': self.container_format,
            'properties': {'id': image_id}
        }
        images = [i for i in glance.images.list(filters=filters)]
        if images:
            return images[0]

    def _clear_images_name(self, glance, image_name):
        images = glance.images.list(filters={'name': image_name})
        for image in images:
            image.update(name=None, purge_props=False)

    def _handler_tag_created(self, sender, namespace, repository, tag, value):
        glance = self._create_glance_client()
        image = self._find_image_by_id(glance, value)
        if not image:
            # No corresponding image, ignoring
            return
        image_name = '{0}:{1}'.format(repository, tag)
        if namespace != 'library':
            image_name = '{0}/{1}'.format(namespace, image_name)
        # Clear any previous image tagged with this name
        self._clear_images_name(glance, image_name)
        image.update(name=image_name, purge_props=False)

    def _handler_tag_deleted(self, sender, namespace, repository, tag):
        image_name = '{0}:{1}'.format(repository, tag)
        if namespace != 'library':
            image_name = '{0}/{1}'.format(namespace, image_name)
        glance = self._create_glance_client()
        self._clear_images_name(glance, image_name)

    def get_content(self, path):
        (image, propname) = self._init_path(path, False)
        if not propname:
            raise ValueError('Wrong call (should be stream_read)')
        if not image or propname not in image.properties:
            raise IOError('No such image {0}'.format(path))
        return image.properties[propname]

    def put_content(self, path, content):
        (image, propname) = self._init_path(path)
        if not propname:
            raise ValueError('Wrong call (should be stream_write)')
        if 'meta__files' in propname:
            return
        props = {propname: content}
        image.update(properties=props, purge_props=False)

    def stream_read(self, path, bytes_range=None):
        (image, propname) = self._init_path(path, False)
        if propname:
            raise ValueError('Wrong call (should be get_content)')
        if not image:
            raise IOError('No such image {0}'.format(path))
        return image.data(do_checksum=False)

    def stream_write(self, path, fp):
        (image, propname) = self._init_path(path)
        if propname:
            raise ValueError('Wrong call (should be put_content)')
        image.update(data=fp, purge_props=False)

    def exists(self, path):
        (image, propname) = self._init_path(path, False)
        if not image:
            return False
        if not propname:
            return True
        return (propname in image.properties)

    def is_private(self, namespace, repository):
        return False

    def remove(self, path):
        (image, propname) = self._init_path(path, False)
        if not image:
            return
        if propname:
            # Delete only the image property
            props = image.properties
            if propname in props:
                del props[propname]
                image.update(properties=props)
            return
        image.delete()

    def get_size(self, path):
        (image, propname) = self._init_path(path, False)
        if not image:
            raise OSError('No such image: \'{0}\''.format(path))
        return image.size
