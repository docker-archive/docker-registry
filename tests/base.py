# -*- coding: utf-8 -*-

import hashlib
import os
import random
import string
import unittest

from docker_registry.core import compat
import docker_registry.wsgi as wsgi

data_dir = os.path.join(os.path.dirname(__file__), "data")


class TestCase(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        unittest.TestCase.__init__(self, *args, **kwargs)
        wsgi.app.testing = True
        self.http_client = wsgi.app.test_client()
        # Override the method so we can set headers for every single call
        orig_open = self.http_client.open

        def _open(*args, **kwargs):
            if 'headers' not in kwargs:
                kwargs['headers'] = {}
            if 'User-Agent' not in kwargs['headers']:
                ua = ('docker/0.10.1 go/go1.2.1 git-commit/3600720 '
                      'kernel/3.8.0-19-generic os/linux arch/amd64')
                kwargs['headers']['User-Agent'] = ua
            return orig_open(*args, **kwargs)
        self.http_client.open = _open

    def gen_random_string(self, length=16):
        return ''.join([random.choice(string.ascii_uppercase + string.digits)
                        for x in range(length)]).lower()

    def set_image_checksum(self, image_id, checksum):
        headers = {'X-Docker-Checksum-Payload': checksum}
        url = '/v1/images/{0}/checksum'.format(image_id)
        resp = self.http_client.put(url, headers=headers)
        self.assertEqual(resp.status_code, 200, resp.data)
        # Once the checksum test passed, the image is "locked"
        resp = self.http_client.put(url, headers=headers)
        self.assertEqual(resp.status_code, 409, resp.data)
        # Cannot set the checksum on an non-existing image
        url = '/v1/images/{0}/checksum'.format(self.gen_random_string())
        resp = self.http_client.put(url, headers=headers)
        self.assertEqual(resp.status_code, 404, resp.data)

    def upload_image(self, image_id, parent_id, layer):
        json_obj = {
            'id': image_id
        }
        if parent_id:
            json_obj['parent'] = parent_id
        json_data = compat.json.dumps(json_obj)
        h = hashlib.sha256(json_data + '\n')
        h.update(layer)
        layer_checksum = 'sha256:{0}'.format(h.hexdigest())
        headers = {'X-Docker-Payload-Checksum': layer_checksum}
        resp = self.http_client.put('/v1/images/{0}/json'.format(image_id),
                                    headers=headers,
                                    data=json_data)
        self.assertEqual(resp.status_code, 200, resp.data)
        # Make sure I cannot download the image before push is complete
        resp = self.http_client.get('/v1/images/{0}/json'.format(image_id))
        self.assertEqual(resp.status_code, 400, resp.data)
        layer_file = compat.StringIO(layer)
        resp = self.http_client.put('/v1/images/{0}/layer'.format(image_id),
                                    input_stream=layer_file)
        layer_file.close()
        self.assertEqual(resp.status_code, 200, resp.data)
        self.set_image_checksum(image_id, layer_checksum)
        # Push done, test reading the image
        resp = self.http_client.get('/v1/images/{0}/json'.format(image_id))
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.headers.get('x-docker-size'), str(len(layer)))
        self.assertEqual(resp.headers['x-docker-checksum-payload'],
                         layer_checksum)
