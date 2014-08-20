# -*- coding: utf-8 -*-

import base

from docker_registry.core import compat
json = compat.json


class TestTags(base.TestCase):

    def test_simple(self, repos_name=None):
        if repos_name is None:
            repos_name = self.gen_random_string()
        image_id = self.gen_random_string()
        layer_data = self.gen_random_string(1024)
        self.upload_image(image_id, parent_id=None, layer=layer_data)

        # test tags create
        url = '/v1/repositories/foo/{0}/tags/latest'.format(repos_name)
        headers = {'User-Agent':
                   'docker/0.7.2-dev go/go1.2 os/ostest arch/archtest'}
        resp = self.http_client.put(url,
                                    headers=headers,
                                    data=json.dumps(image_id))
        self.assertEqual(resp.status_code, 200, resp.data)
        url = '/v1/repositories/foo/{0}/tags/test'.format(repos_name)
        resp = self.http_client.put(url,
                                    data=json.dumps(image_id))
        self.assertEqual(resp.status_code, 200, resp.data)

        # test tags read
        url = '/v1/repositories/foo/{0}/tags/latest'.format(repos_name)
        resp = self.http_client.get(url)
        self.assertEqual(resp.status_code, 200, resp.data)
        # Note(dmp): unicode patch XXX not applied assume requests does the job
        self.assertEqual(json.loads(resp.data), image_id, resp.data)

        # test repository json
        url = '/v1/repositories/foo/{0}/json'.format(repos_name)
        resp = self.http_client.get(url)
        self.assertEqual(resp.status_code, 200, resp.data)
        # Note(dmp): unicode patch XXX not applied assume requests does the job
        props = json.loads(resp.data)
        self.assertEqual(props['docker_version'], '0.7.2-dev')
        self.assertEqual(props['docker_go_version'], 'go1.2')
        self.assertEqual(props['os'], 'ostest')
        self.assertEqual(props['arch'], 'archtest')

        # test repository tags json
        url = '/v1/repositories/foo/{0}/tags/latest/json'.format(repos_name)
        resp = self.http_client.get(url)
        self.assertEqual(resp.status_code, 200, resp.data)
        # Note(dmp): unicode patch XXX not applied assume requests does the job
        props = json.loads(resp.data)
        self.assertEqual(props['docker_version'], '0.7.2-dev')
        self.assertEqual(props['docker_go_version'], 'go1.2')
        self.assertEqual(props['os'], 'ostest')
        self.assertEqual(props['arch'], 'archtest')

        # test tags update
        url = '/v1/repositories/foo/{0}/tags/latest'.format(repos_name)
        headers = {'User-Agent':
                   'docker/0.7.2-dev go/go1.2 os/ostest arch/changedarch'}
        resp = self.http_client.put(url,
                                    headers=headers,
                                    data=json.dumps(image_id))
        self.assertEqual(resp.status_code, 200, resp.data)
        url = '/v1/repositories/foo/{0}/tags/test'.format(repos_name)
        resp = self.http_client.put(url,
                                    headers=headers,
                                    data=json.dumps(image_id))
        self.assertEqual(resp.status_code, 200, resp.data)

        # test repository latest tag json update
        url = '/v1/repositories/foo/{0}/tags/latest/json'.format(repos_name)
        resp = self.http_client.get(url)
        self.assertEqual(resp.status_code, 200, resp.data)
        # Note(dmp): unicode patch XXX not applied assume requests does the job
        props = json.loads(resp.data)
        self.assertEqual(props['docker_version'], '0.7.2-dev')
        self.assertEqual(props['docker_go_version'], 'go1.2')
        self.assertEqual(props['os'], 'ostest')
        self.assertEqual(props['arch'], 'changedarch')

        # test repository test tag json update
        url = '/v1/repositories/foo/{0}/tags/test/json'.format(repos_name)
        resp = self.http_client.get(url)
        self.assertEqual(resp.status_code, 200, resp.data)
        # Note(dmp): unicode patch XXX not applied assume requests does the job
        props = json.loads(resp.data)
        self.assertEqual(props['docker_version'], '0.7.2-dev')
        self.assertEqual(props['docker_go_version'], 'go1.2')
        self.assertEqual(props['os'], 'ostest')
        self.assertEqual(props['arch'], 'changedarch')

        # test tags list
        url = '/v1/repositories/foo/{0}/tags'.format(repos_name)
        resp = self.http_client.get(url)
        self.assertEqual(resp.status_code, 200, resp.data)
        # Note(dmp): unicode patch XXX not applied assume requests does the job
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
        url = '/v1/repositories/foo/{0}/'.format(repos_name)
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
