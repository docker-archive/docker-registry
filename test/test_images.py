
import json

import base


class TestImages(base.TestCase):

    def test_unset_nginx_accel_redirect_layer(self):
        image_id = self.gen_random_string()
        layer_data = self.gen_random_string(1024)
        self.upload_image(image_id, parent_id=None, layer=layer_data)

        resp = self.http_client.get('/v1/images/{0}/layer'.format(image_id))

        self.assertEqual(layer_data, resp.data)

    def test_nginx_accel_redirect_layer(self):
        image_id = self.gen_random_string()
        layer_data = self.gen_random_string(1024)
        self.upload_image(image_id, parent_id=None, layer=layer_data)

        import registry.images

        # ensure the storage mechanism is LocalStorage or this test is bad
        import storage.local
        self.assertTrue(isinstance(registry.images.store,
                        storage.local.LocalStorage),
                        'Store must be LocalStorage')

        # set the nginx accel config
        accel_header = 'X-Accel-Redirect'
        accel_prefix = '/registry'
        registry.images.cfg._config['nginx_x_accel_redirect'] = accel_prefix

        layer_path = 'images/{0}/layer'.format(image_id)

        try:
            resp = self.http_client.get('/v1/{}'.format(layer_path))
            self.assertTrue(accel_header in resp.headers)

            expected = '{}/{}'.format(accel_prefix, layer_path)
            self.assertEqual(expected, resp.headers[accel_header])

            self.assertEqual('', resp.data)
        finally:
            registry.images.cfg._config.pop('nginx_x_accel_redirect')

    def test_simple(self):
        image_id = self.gen_random_string()
        parent_id = self.gen_random_string()
        layer_data = self.gen_random_string(1024)
        self.upload_image(parent_id, parent_id=None, layer=layer_data)
        self.upload_image(image_id, parent_id=parent_id, layer=layer_data)
        # test fetching the ancestry
        resp = self.http_client.get('/v1/images/{0}/ancestry'.format(image_id))
        ancestry = json.loads(resp.data)
        self.assertEqual(len(ancestry), 2)
        self.assertEqual(ancestry[0], image_id)
        self.assertEqual(ancestry[1], parent_id)

    def test_notfound(self):
        resp = self.http_client.get('/v1/images/{0}/json'.format(
            self.gen_random_string()))
        self.assertEqual(resp.status_code, 404, resp.data)

    def test_set_checksum_after(self):
        def set_checksum_callback(image_id, checksum):
            headers = {'X-Docker-Checksum': checksum}
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

        image_id = self.gen_random_string()
        layer_data = self.gen_random_string(1024)
        self.upload_image(image_id,
                          parent_id=None,
                          layer=layer_data,
                          set_checksum_callback=set_checksum_callback)
