
import json

import base


class TestTags(base.TestCase):

    def test_simple(self, repos_name=None):
        if repos_name is None:
            repos_name = self.gen_random_string()
        image_id = self.gen_random_string()
        layer_data = self.gen_random_string(1024)
        self.upload_image(image_id, parent_id=None, layer=layer_data)
        # test tags create
        url = '/v1/repositories/foo/{0}/tags/latest'.format(repos_name)
        resp = self.http_client.put(url,
                                    data=json.dumps(image_id))
        self.assertEqual(resp.status_code, 200, resp.data)
        url = '/v1/repositories/foo/{0}/tags/test'.format(repos_name)
        resp = self.http_client.put(url,
                                    data=json.dumps(image_id))
        self.assertEqual(resp.status_code, 200, resp.data)
        # test tags list
        url = '/v1/repositories/foo/{0}/tags'.format(repos_name)
        resp = self.http_client.get(url)
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(len(json.loads(resp.data)), 2, resp.data)
        # test tag delete
        url = '/v1/repositories/foo/{0}/tags/latest'.format(repos_name)
        resp = self.http_client.delete(url)
        self.assertEqual(resp.status_code, 200, resp.data)
        url = '/v1/repositories/foo/{0}/tags'.format(repos_name)
        resp = self.http_client.get(url)
        self.assertEqual(resp.status_code, 200, resp.data)
        url = '/v1/repositories/foo/{0}/tags/latest'.format(repos_name)
        resp = self.http_client.get(url)
        self.assertEqual(resp.status_code, 404, resp.data)
        # test whole delete
        url = '/v1/repositories/foo/{0}/tags'.format(repos_name)
        resp = self.http_client.delete(url)
        self.assertEqual(resp.status_code, 200, resp.data)
        url = '/v1/repositories/foo/{0}/tags'.format(repos_name)
        resp = self.http_client.get(url)
        self.assertEqual(resp.status_code, 404, resp.data)

    def test_notfound(self):
        notexist = self.gen_random_string()
        url = '/v1/repositories/{0}/bar/tags'.format(notexist)
        resp = self.http_client.get(url)
        self.assertEqual(resp.status_code, 404, resp.data)

    def test_special_chars(self):
        repos_name = '{0}%$_-test'.format(self.gen_random_string(5))
        self.test_simple(repos_name)
