
import os
import sys
import json
import string
import random
import hashlib
import unittest
from cStringIO import StringIO

root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(root_path)
sys.path.append(os.path.join(root_path, 'lib'))

os.environ['SETTINGS_FLAVOR'] = 'test'

import registry


class TestCase(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        unittest.TestCase.__init__(self, *args, **kwargs)
        registry.app.testing = True
        self.http_client = registry.app.test_client()

    def gen_random_string(self, length=16):
        return ''.join([random.choice(string.ascii_uppercase + string.digits)
            for x in range(length)]).lower()

    def upload_image(self, image_id, parent_id, layer):
        json_data = {
            'id': image_id
            }
        if parent_id:
            json_data['parent'] = parent_id
        h = hashlib.sha256(json.dumps(json_data, sort_keys=True) + '\n')
        h.update(layer)
        layer_checksum = 'sha256:{0}'.format(h.hexdigest())
        resp = self.http_client.put('/v1/images/{0}/json'.format(image_id),
                data=json.dumps(json_data))
        self.assertEqual(resp.status_code, 200, resp.data)
        # Make sure I cannot download the image before push is complete
        resp = self.http_client.get('/v1/images/{0}/json'.format(image_id))
        self.assertEqual(resp.status_code, 400, resp.data)
        layer_file = StringIO(layer)
        resp = self.http_client.put('/v1/images/{0}/layer'.format(image_id),
                input_stream=layer_file,
                headers={'X-Docker-Checksum': layer_checksum})
        layer_file.close()
        self.assertEqual(resp.status_code, 200, resp.data)
