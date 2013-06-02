
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
        resp = self.http_client.put(
                '/v1/repositories/foo/{0}/tags/latest'.format(repos_name),
                data=json.dumps(image_id))
        self.assertEqual(resp.status_code, 200, resp.data)
        resp = self.http_client.put(
                '/v1/repositories/foo/{0}/tags/test'.format(repos_name),
                data=json.dumps(image_id))
        self.assertEqual(resp.status_code, 200, resp.data)
        # test tags list
        resp = self.http_client.get(
                '/v1/repositories/foo/{0}/tags'.format(repos_name))
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(len(json.loads(resp.data)), 2, resp.data)
        # test tag delete
        resp = self.http_client.delete(
                '/v1/repositories/foo/{0}/tags/latest'.format(repos_name))
        self.assertEqual(resp.status_code, 200, resp.data)
        resp = self.http_client.get(
                '/v1/repositories/foo/{0}/tags'.format(repos_name))
        self.assertEqual(resp.status_code, 200, resp.data)
        resp = self.http_client.get(
                '/v1/repositories/foo/{0}/tags/latest'.format(repos_name))
        self.assertEqual(resp.status_code, 404, resp.data)
        # test whole delete
        resp = self.http_client.delete(
                '/v1/repositories/foo/{0}/'.format(repos_name))
        self.assertEqual(resp.status_code, 200, resp.data)
        resp = self.http_client.get(
                '/v1/repositories/foo/{0}/tags'.format(repos_name))
        self.assertEqual(resp.status_code, 404, resp.data)

    def test_notfound(self):
        notexist = self.gen_random_string()
        resp = self.http_client.get(
                '/v1/repositories/{0}/bar/tags'.format(notexist))
        self.assertEqual(resp.status_code, 404, resp.data)

    def test_special_chars(self):
        self.test_simple(
                repos_name='{0}%$_-test'.format(self.gen_random_string(5)))
