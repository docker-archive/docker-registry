
import gevent.monkey
gevent.monkey.patch_all()

import logging

import boto.gs.connection
import boto.gs.key

import cache_lru

from boto_base import BotoStorage


logger = logging.getLogger(__name__)


def _UpdateSysPath(config):
    import sys

    cloud_sdk_path = config.cloud_sdk_path or '/google-cloud-sdk/'
    gsutil_path =  cloud_sdk_path + 'platform/gsutil/'
    gsutil_third_party_path = gsutil_path + 'third_party/'

    # oauth2client
    sys.path.append(cloud_sdk_path + 'lib/')

    # gslib.*
    sys.path.append(gsutil_path)

    # httplib2
    sys.path.append(gsutil_third_party_path + 'httplib2/python2')

    # sock.py
    sys.path.append(gsutil_third_party_path + 'httplib2/python2/httplib2')

    sys.path.append(gsutil_third_party_path + 'retry-decorator')


def _LoadOauth2Plugin():
    import threading

    try:
        from gslib.third_party.oauth2_plugin import oauth2_plugin # flake8: noqa
        from gslib.third_party.oauth2_plugin import oauth2_client
        oauth2_client.token_exchange_lock = threading.Lock()

    except ImportError:
        logger.error('To use OAuth 2.0 with Google Cloud Storage install '
                     'Google Cloud SDK and set cloud_sdk_path in config.yml. '
                     'For more info see https://developers.google.com/cloud/sdk/')


class GSStorage(BotoStorage):

    def __init__(self, config):
        BotoStorage.__init__(self, config)

    def makeConnection(self):
        if self._config.oauth2 is True:
            _UpdateSysPath(self._config)
            _LoadOauth2Plugin()

            uri = boto.storage_uri(self._config.boto_bucket, 'gs')
            return uri.connect()

        return boto.gs.connection.GSConnection(
            self._config.gs_access_key,
            self._config.gs_secret_key,
            is_secure=(self._config.gs_secure is True))

    def makeKey(self, path):
        return boto.gs.key.Key(self._boto_bucket, path)

    @cache_lru.put
    def put_content(self, path, content):
        path = self._init_path(path)
        key = self.makeKey(path)
        key.set_contents_from_string(content)
        return path

    def stream_write(self, path, fp):
        # Minimum size of upload part size on GS is 5MB
        buffer_size = 5 * 1024 * 1024
        if self.buffer_size > buffer_size:
            buffer_size = self.buffer_size
        path = self._init_path(path)
        key = self.makeKey(path)
        key.set_contents_from_string(fp.read())
