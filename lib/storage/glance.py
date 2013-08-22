
import os

import glanceclient

from signals import tag_created, tag_deleted
from . import Storage
from .s3 import S3Storage
from .local import LocalStorage


TAGS = 0
LAYERS = 1


class GlanceStorage(Storage):

    """ This module stores the image layers into OpenStack Glance.
        However tags are still stored on other filesystem-like stores.
    """

    def __init__(self, config):
        self._config = config
        self._storage_layers = GlanceStorageLayers(config)
        kind = config.get('storage_alternate', 'local')
        if kind == 's3':
            self._storage_tags = S3Storage(config)
        elif kind == 'local':
            self._storage_tags = LocalStorage(config)
        else:
            raise ValueError('Not supported storage \'{0}\''.format(kind))

    def _find_path_type(self, *args, **kwargs):
        if 'path' in kwargs:
            path = kwargs['path']
        elif len(args > 0) and isinstance(args[0], basestring):
            path = args[0]
        else:
            return
        if path.startswith(self.images):
            return LAYERS
        if path.startswith(self.repositories):
            return TAGS

    def __getattr__(self, name):
        def dispatcher(*args, **kwargs):
            kind = self._find_path_type(*args, **kwargs)
            if kind == TAGS:
                return self._storage_tags(*args, **kwargs)
            if kind == LAYERS:
                return self._storage_layers(*args, **kwargs)
            raise ValueError('Cannot dispath method '
                             '"{0}" args: {1} {2}'.format(name,
                                                          *args,
                                                          **kwargs))
        return dispatcher


class GlanceStorageLayers(Storage):

    def __init__(self, config):
        self._config = config

    def _create_glance_client(self):
        #FIXME(sam) the token is taken from the environ for testing only!
        endpoint = self._config.glance_endpoint
        return glanceclient.Client('1', endpoint=endpoint,
                                   token=os.environ['OS_AUTH_TOKEN'])

    def _init_path(self, path, create=True):
        """ This resolve a standard Docker Registry path
            and returns: glance_image_id, property_name
            If property name is None, we're want to reach the image_data
        """
        parts = path.split('/')
        if len(parts) != 3 or parts[0] != self.images:
            raise ValueError('Invalid path: {0}'.format(path))
        image_id = parts[1]
        filename = parts[2]
        glance = self._create_glance_client()
        image = self._find_image_by_id(glance, image_id)
        if not image and create is True:
            #FIXME(sam): set diskformat and container format
            image = glance.images.create()
        propname = 'meta-{0}'.format(filename)
        if filename == 'layer':
            propname = None
        return image, propname

    def _find_image_by_id(self, glance, image_id):
        #FIXME(samalba): add a filter for docker image format
        filters = {
            'properties': {'id': image_id}
        }
        images = [i for i in glance.images.list(filters=filters)]
        if images:
            return images[0]

    def _clear_images_name(self, glance, image_name):
        images = glance.images.list(filters={'name': image_name})
        for image in images:
            image.update(name=None)

    @tag_created.connect
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
        image.update(name=image_name)

    @tag_deleted.connect
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
        props = image.properties
        props[propname] = content
        image.update(properties=props)

    def stream_read(self, path):
        (image, propname) = self._init_path(path, False)
        if propname:
            raise ValueError('Wrong call (should be get_content)')
        if not image:
            raise IOError('No such image {0}'.format(path))
        return image.data

    def stream_write(self, path, fp):
        (image, propname) = self._init_path(path)
        if propname:
            raise ValueError('Wrong call (should be put_content)')
        image.update(data=fp)

    def exists(self, path):
        (image, propname) = self._init_path(path, False)
        if not image:
            return False
        if not propname:
            return True
        return (propname in image.properties)

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
