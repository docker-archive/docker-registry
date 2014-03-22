import cStringIO as StringIO
import hashlib
import json
import os

import requests

from docker_registry.lib import checksums
from docker_registry.lib import config
from docker_registry import storage

import base


cfg = config.load()


class TestWorkflow(base.TestCase):

    # Dev server needs to run on port 5000 in order to run this test
    registry_endpoint = os.environ.get(
        'DOCKER_REGISTRY_ENDPOINT',
        'https://registrystaging-docker.dotcloud.com')
    #registry_endpoint = 'http://localhost:5000'
    index_endpoint = os.environ.get(
        'DOCKER_INDEX_ENDPOINT',
        'https://indexstaging-docker.dotcloud.com')
    # export DOCKER_CREDS="login:password"
    user_credentials = os.environ['DOCKER_CREDS'].split(':')
    cookies = None

    def generate_chunk(self, data):
        bufsize = 1024
        io = StringIO.StringIO(data)
        while True:
            buf = io.read(bufsize)
            if not buf:
                return
            yield buf
        io.close()

    def update_cookies(self, response):
        cookies = response.cookies
        if cookies:
            self.cookies = cookies

    def upload_image(self, image_id, parent_id, token):
        layer = self.gen_random_string(7 * 1024 * 1024)
        json_obj = {
            'id': image_id
        }
        if parent_id:
            json_obj['parent'] = parent_id
        json_data = json.dumps(json_obj)
        h = hashlib.sha256(json_data + '\n')
        h.update(layer)
        layer_checksum = 'sha256:{0}'.format(h.hexdigest())
        resp = requests.put('{0}/v1/images/{1}/json'.format(
            self.registry_endpoint, image_id),
            data=json_data,
            headers={'Authorization': 'Token ' + token,
                     'X-Docker-Checksum': layer_checksum},
            cookies=self.cookies)
        self.assertEqual(resp.status_code, 200, resp.text)
        self.update_cookies(resp)
        resp = requests.put('{0}/v1/images/{1}/layer'.format(
            self.registry_endpoint, image_id),
            data=self.generate_chunk(layer),
            headers={'Authorization': 'Token ' + token},
            cookies=self.cookies)
        self.assertEqual(resp.status_code, 200, resp.text)
        self.update_cookies(resp)
        return {'id': image_id, 'checksum': layer_checksum}

    def update_tag(self, namespace, repos, image_id, tag_name):
        resp = requests.put('{0}/v1/repositories/{1}/{2}/tags/{3}'.format(
            self.registry_endpoint, namespace, repos, tag_name),
            data=json.dumps(image_id),
            cookies=self.cookies)
        self.assertEqual(resp.status_code, 200, resp.text)
        self.update_cookies(resp)

    def docker_push(self):
        # Test Push
        self.image_id = self.gen_random_string()
        self.parent_id = self.gen_random_string()
        image_id = self.image_id
        parent_id = self.parent_id
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
            headers={'X-Endpoints': self.registry_endpoint},
            data=json.dumps(images_json))
        self.assertEqual(resp.status_code, 204)
        return (namespace, repos)

    def fetch_image(self, image_id):
        """Return image json metadata, checksum and its blob."""
        resp = requests.get('{0}/v1/images/{1}/json'.format(
            self.registry_endpoint, image_id),
            cookies=self.cookies)
        self.assertEqual(resp.status_code, 200, resp.text)
        self.update_cookies(resp)
        json_data = resp.text
        checksum = resp.headers['x-docker-checksum']
        resp = requests.get('{0}/v1/images/{1}/layer'.format(
            self.registry_endpoint, image_id),
            cookies=self.cookies)
        self.assertEqual(resp.status_code, 200, resp.text)
        self.update_cookies(resp)
        return (json_data, checksum, resp.text)

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
        self.update_cookies(resp)
        self.assertEqual(resp.status_code, 200, resp.text)
        ancestry = json.loads(resp.text)
        # We got the ancestry, let's fetch all the images there
        for image_id in ancestry:
            json_data, checksum, blob = self.fetch_image(image_id)
            # check queried checksum and local computed checksum from the image
            # are the same
            tmpfile = StringIO.StringIO()
            tmpfile.write(blob)
            tmpfile.seek(0)
            computed_checksum = checksums.compute_simple(tmpfile, json_data)
            tmpfile.close()
            self.assertEqual(checksum, computed_checksum)
        # Remove the repository
        resp = requests.delete('{0}/v1/repositories/{1}/{2}/'.format(
            self.registry_endpoint, namespace, repos), cookies=self.cookies)
        self.assertEqual(resp.status_code, 200, resp.text)
        self.update_cookies(resp)
        # Remove image_id, then parent_id
        store = storage.load()
        store.remove(os.path.join(store.images, self.image_id))
        store.remove(os.path.join(store.images, self.parent_id))

    def test_workflow(self):
        (namespace, repos) = self.docker_push()
        self.docker_pull(namespace, repos)
