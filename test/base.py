
import cStringIO as StringIO
import hashlib
import json
import random
import string
import unittest

import docker_registry


class TestCase(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        unittest.TestCase.__init__(self, *args, **kwargs)
        docker_registry.app.testing = True
        self.http_client = docker_registry.app.test_client()
        # Override the method so we can set headers for every single call
        orig_open = self.http_client.open

        def _open(*args, **kwargs):
            if 'headers' not in kwargs:
                kwargs['headers'] = {}
            if 'User-Agent' not in kwargs['headers']:
                ua = ('docker/0.0 go/go1.2.1 git-commit/3600720 '
                      'kernel/3.8.0-19-generic os/linux arch/amd64')
                kwargs['headers']['User-Agent'] = ua
            return orig_open(*args, **kwargs)
        self.http_client.open = _open

    def gen_random_string(self, length=16):
        return ''.join([random.choice(string.ascii_uppercase + string.digits)
                        for x in range(length)]).lower()

    def upload_image(self, image_id, parent_id, layer,
                     set_checksum_callback=None):
        json_obj = {
            'id': image_id
        }
        if parent_id:
            json_obj['parent'] = parent_id
        json_data = json.dumps(json_obj)
        h = hashlib.sha256(json_data + '\n')
        h.update(layer)
        layer_checksum = 'sha256:{0}'.format(h.hexdigest())
        headers = {'X-Docker-Checksum': layer_checksum}
        if set_checksum_callback:
            headers = {}
        resp = self.http_client.put('/v1/images/{0}/json'.format(image_id),
                                    headers=headers,
                                    data=json_data)
        self.assertEqual(resp.status_code, 200, resp.data)
        # Make sure I cannot download the image before push is complete
        resp = self.http_client.get('/v1/images/{0}/json'.format(image_id))
        self.assertEqual(resp.status_code, 400, resp.data)
        layer_file = StringIO.StringIO(layer)
        resp = self.http_client.put('/v1/images/{0}/layer'.format(image_id),
                                    input_stream=layer_file)
        layer_file.close()
        self.assertEqual(resp.status_code, 200, resp.data)
        if set_checksum_callback:
            set_checksum_callback(image_id, layer_checksum)
        # Push done, test reading the image
        resp = self.http_client.get('/v1/images/{0}/json'.format(image_id))
        self.assertEqual(resp.headers.get('x-docker-size'), str(len(layer)))
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.headers['x-docker-checksum'], layer_checksum)
