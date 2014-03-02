
import gevent.monkey
gevent.monkey.patch_all()

import logging

import boto.gs.connection
import boto.gs.key

import cache_lru

from boto_base import BotoStorage


logger = logging.getLogger(__name__)


class GSStorage(BotoStorage):

    def __init__(self, config):
        BotoStorage.__init__(self, config)

    def makeConnection(self):
        if self._config.oauth2 is True:
            try:
                import sys
                import threading

                from gslib.third_party.oauth2_plugin import oauth2_plugin
                from gslib.third_party.oauth2_plugin import oauth2_client

                oauth2_client.token_exchange_lock = threading.Lock()

                uri = boto.storage_uri(self._config.boto_bucket, 'gs')
                return uri.connect()
            except ImportError:
                logger.error('To use OAuth 2.0 with Google Cloud Storage '
                             ' gsutil must be installed ('
                             '"https://developers.google.com/storage/docs/'
                             'gsutil_install")')
                sys.exit(1)

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
