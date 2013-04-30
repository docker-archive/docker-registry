
import os
from cStringIO import StringIO
import json
import hashlib
import requests
import base
import config

cfg = config.load()


class TestWorkflow(base.TestCase):

    # Dev server needs to run on port 5000 in order to run this test
    #registry_endpoint = 'https://registrystaging-docker.dotcloud.com'
    registry_endpoint = 'http://localhost:5000'
    index_endpoint = 'https://indexstaging-docker.dotcloud.com'
    # export DOCKER_CREDS="login:password"
    user_credentials = os.environ['DOCKER_CREDS'].split(':')
    cookies = None

    def generate_chunk(self, data):
        bufsize = 1024
        io = StringIO(data)
        while True:
            buf = io.read(bufsize)
            if not buf:
                return
            yield buf
        io.close()

    def upload_image(self, image_id, parent_id, token):
        layer = self.gen_random_string(7 * 1024 * 1024)
        json_data = {
            'id': image_id
            }
        if parent_id:
            json_data['parent'] = parent_id
        h = hashlib.sha256(json.dumps(json_data, sort_keys=True) + '\n')
        h.update(layer)
        layer_checksum = 'sha256:{0}'.format(h.hexdigest())
        resp = requests.put('{0}/v1/images/{1}/json'.format(
            self.registry_endpoint, image_id),
            data=json.dumps(json_data),
            headers={'Authorization': 'Token ' + token},
            cookies=self.cookies)
        self.assertEqual(resp.status_code, 200, resp.text)
        self.cookies = resp.cookies
        resp = requests.put('{0}/v1/images/{1}/layer'.format(
            self.registry_endpoint, image_id),
            data=self.generate_chunk(layer),
            headers={
                'Authorization': 'Token ' + token,
                'X-Docker-Checksum': layer_checksum},
            cookies=self.cookies)
        self.assertEqual(resp.status_code, 200, resp.text)
        self.cookies = resp.cookies
        return {'id': image_id, 'checksum': layer_checksum}

    def update_tag(self, namespace, repos, image_id, tag_name):
        resp = requests.put('{0}/v1/repositories/{1}/{2}/tags/{3}'.format(
            self.registry_endpoint, namespace, repos, tag_name),
            data=json.dumps(image_id),
            cookies=self.cookies)
        self.assertEqual(resp.status_code, 200, resp.text)
        self.cookies = resp.cookies

    def docker_push(self):
        # Test Push
        image_id = self.gen_random_string()
        parent_id = self.gen_random_string()
        namespace = self.user_credentials[0]
        repos = self.gen_random_string()
        # Docker -> Index
        images_json = json.dumps([{'id': image_id}, {'id': parent_id}])
        resp = requests.put('{0}/v1/repositories/{1}/{2}/'.format(
            self.index_endpoint, namespace, repos),
            auth=tuple(self.user_credentials),
            headers={'X-Docker-Token': 'true'},
            data=images_json)
        self.assertEqual(resp.status_code, 200, resp.text)
        token = resp.headers.get('x-docker-token')
        # Docker -> Registry
        images_json = []
        images_json.append(self.upload_image(parent_id, None, token))
        images_json.append(self.upload_image(image_id, parent_id, token))
        # Updating the tags does not need a token, it will use the Cookie
        self.update_tag(namespace, repos, image_id, 'latest')
        # Docker -> Index
        resp = requests.put('{0}/v1/repositories/{1}/{2}/images'.format(
            self.index_endpoint, namespace, repos),
            auth=tuple(self.user_credentials),
            headers={'X-Endpoints': 'registrystaging-docker.dotcloud.com'},
            data=json.dumps(images_json))
        self.assertEqual(resp.status_code, 204)
        return (namespace, repos)

    def fetch_image(self, image_id):
        resp = requests.get('{0}/v1/images/{1}/json'.format(
            self.registry_endpoint, image_id),
            cookies=self.cookies)
        self.assertEqual(resp.status_code, 200, resp.text)
        self.cookies = resp.cookies
        resp = requests.get('{0}/v1/images/{1}/layer'.format(
            self.registry_endpoint, image_id),
            cookies=self.cookies)
        self.assertEqual(resp.status_code, 200, resp.text)
        self.cookies = resp.cookies

    def docker_pull(self, namespace, repos):
        # Test pull
        # Docker -> Index
        resp = requests.get('{0}/v1/repositories/{1}/{2}/images'.format(
            self.index_endpoint, namespace, repos),
            auth=tuple(self.user_credentials),
            headers={'X-Docker-Token': 'true'})
        self.assertEqual(resp.status_code, 200)
        token = resp.headers.get('x-docker-token')
        # Here we should use the 'X-Endpoints' returned in a real environment
        # Docker -> Registry
        resp = requests.get('{0}/v1/repositories/{1}/{2}/tags/latest'.format(
                self.registry_endpoint, namespace, repos),
                headers={'Authorization': 'Token ' + token})
        self.assertEqual(resp.status_code, 200, resp.text)
        self.cookies = resp.cookies
        # Docker -> Registry
        image_id = json.loads(resp.text)
        resp = requests.get('{0}/v1/images/{1}/ancestry'.format(
            self.registry_endpoint, image_id),
            cookies=self.cookies)
        self.cookies = resp.cookies
        self.assertEqual(resp.status_code, 200, resp.text)
        ancestry = json.loads(resp.text)
        # We got the ancestry, let's fetch all the images there
        for image_id in ancestry:
            self.fetch_image(image_id)
        # FIXME: fetch and check the checksums

    def test_workflow(self):
        (namespace, repos) = self.docker_push()
        self.docker_pull(namespace, repos)
