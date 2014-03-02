
import gevent.monkey
gevent.monkey.patch_all()

import logging

import sys
import threading

import boto.storage_uri

from gcs import GSStorage


logger = logging.getLogger(__name__)


class GSOAuth2Storage(GSStorage):

    def __init__(self, config):
        try:
            from gslib.third_party.oauth2_plugin import oauth2_plugin
            from gslib.third_party.oauth2_plugin import oauth2_client
            oauth2_client.token_exchange_lock = threading.Lock()
        except ImportError:
            logger.error('To use OAuth 2.0 with Google Cloud Storage '
                         ' gsutil must be installed ('
                         'https://developers.google.com/storage/docs/gsutil_install)')
            sys.exit(1)


        GSStorage.__init__(self, config)

    def makeConnection(self):
        self.uri = boto.storage_uri(self._config.boto_bucket, 'gs')
        return self.uri.connect()
