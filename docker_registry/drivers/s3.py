# -*- coding: utf-8 -*-
"""
docker_registry.drivers.s3
~~~~~~~~~~~~~~~~~~~~~~~~~~

This is a s3 based driver.

"""

# This fixes an issue where boto sends unicode to gevent.socket.getaddrinfo in
# an eventlet causing the event pool to hang in a deadlock state.
# This initiates the unicode => idna conversion outside of getaddrinfo,
# preventing the deadlock.
# See https://github.com/gevent/gevent/issues/349 for context.
u'fix for gevent deadlock'.encode('idna')

import gevent.monkey
gevent.monkey.patch_all()

import docker_registry.core.boto as coreboto
from docker_registry.core import compat
from docker_registry.core import exceptions
from docker_registry.core import lru

import logging
import os
import re
import time

import boto.exception
import boto.s3
import boto.s3.connection
import boto.s3.key

logger = logging.getLogger(__name__)


class Cloudfront():
    def __init__(self, awsaccess, awssecret, base, keyid, privatekey):
        boto.connect_cloudfront(
            awsaccess,
            awssecret
        )
        host = re.compile('^https?://([^/]+)').findall(base)
        self.dist = boto.cloudfront.distribution.Distribution(domain_name=host)
        self.base = base
        self.keyid = keyid
        self.privatekey = privatekey
        try:
            self.privatekey = open(privatekey).read()
        except Exception:
            logger.debug('Passed private key is not readable. Assume string.')

    def sign(self, url, expire_time=0):
        path = os.path.join(self.base, url)
        if expire_time:
            expire_time = time.time() + expire_time
        return self.dist.create_signed_url(
            path,
            self.keyid,
            private_key_string=self.privatekey,
            expire_time=int(expire_time)
        )

    def pub(self, path):
        return os.path.join(self.base, path)


class Storage(coreboto.Base):

    def __init__(self, path, config):
        super(Storage, self).__init__(path, config)

    def _build_connection_params(self):
        kwargs = super(Storage, self)._build_connection_params()
        if self._config.s3_secure is not None:
            kwargs['is_secure'] = (self._config.s3_secure is True)
        return kwargs

    def makeConnection(self):
        kwargs = self._build_connection_params()
        # Connect cloudfront if we are required to
        if self._config.cloudfront:
            self.signer = Cloudfront(
                self._config.s3_access_key,
                self._config.s3_secret_key,
                self._config.cloudfront['base'],
                self._config.cloudfront['keyid'],
                self._config.cloudfront['keysecret']
            ).sign
        else:
            self.signer = None

        if self._config.s3_use_sigv4 is True:
            if self._config.boto_host is None:
                logger.warn("No S3 Host specified, Boto won't use SIGV4!")
            boto.config.add_section('s3')
            boto.config.set('s3', 'use-sigv4', 'True')

        if self._config.s3_region is not None:
            return boto.s3.connect_to_region(
                region_name=self._config.s3_region,
                aws_access_key_id=self._config.s3_access_key,
                aws_secret_access_key=self._config.s3_secret_key,
                **kwargs)
        logger.warn("No S3 region specified, using boto default region, " +
                    "this may affect performance and stability.")

        return boto.s3.connection.S3Connection(
            self._config.s3_access_key,
            self._config.s3_secret_key,
            **kwargs)

    def makeKey(self, path):
        return boto.s3.key.Key(self._boto_bucket, path)

    @lru.set
    def put_content(self, path, content):
        path = self._init_path(path)
        key = self.makeKey(path)
        key.set_contents_from_string(
            content, encrypt_key=(self._config.s3_encrypt is True))
        return path

    def stream_write(self, path, fp):
        # Minimum size of upload part size on S3 is 5MB
        buffer_size = 5 * 1024 * 1024
        if self.buffer_size > buffer_size:
            buffer_size = self.buffer_size
        path = self._init_path(path)
        mp = self._boto_bucket.initiate_multipart_upload(
            path, encrypt_key=(self._config.s3_encrypt is True))
        num_part = 1
        try:
            while True:
                buf = fp.read(buffer_size)
                if not buf:
                    break
                io = compat.StringIO(buf)
                mp.upload_part_from_file(io, num_part)
                num_part += 1
                io.close()
        except IOError as e:
            raise e
        mp.complete_upload()

    def content_redirect_url(self, path):
        path = self._init_path(path)
        key = self.makeKey(path)
        if not key.exists():
            raise IOError('No such key: \'{0}\''.format(path))

        # No cloudfront? Sign to the bucket
        if not self.signer:
            return key.generate_url(
                expires_in=1200,
                method='GET',
                query_auth=True)

        # Have cloudfront? Sign it
        return self.signer(path, expire_time=60)

    def get_content(self, path, tries=0):
        try:
            return super(Storage, self).get_content(path)
        except exceptions.FileNotFoundError as e:
            if tries <= 3:
                time.sleep(.1)
                return self.get_content(path, tries + 1)
            else:
                raise e
