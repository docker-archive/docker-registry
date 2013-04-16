
import json
import base


class TestImages(base.TestCase):

    def test_simple(self):
        image_id = self.gen_random_string()
        layer_data = self.gen_random_string(1024)
        self.upload_image(image_id, parent_id=None, layer=layer_data)
        # test the ancestry
        resp = self.http_client.put('/v1/repositories/foo/bar/tags/latest',
                data=json.dumps(image_id))
        self.assertEqual(resp.status_code, 200, resp.data)
        # test tags list
        resp = self.http_client.get('/v1/repositories/foo/bar/tags')
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(len(json.loads(resp.data)), 1, resp.data)
        # test delete
        resp = self.http_client.delete('/v1/repositories/foo/bar/tags/latest')
        self.assertEqual(resp.status_code, 200, resp.data)
        resp = self.http_client.get('/v1/repositories/foo/bar/tags')
        self.assertEqual(resp.status_code, 404, resp.data)

    def test_notfound(self):
        notexist = self.gen_random_string()
        resp = self.http_client.get('/v1/repositories/{0}/bar/tags'.format(notexist))
        self.assertEqual(resp.status_code, 404, resp.data)
