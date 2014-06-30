# -*- coding: utf-8 -*-

import mock
import requests

from docker_registry.lib import config
from docker_registry.lib import mirroring

import base

from docker_registry.core import compat
json = compat.json


def mock_lookup_source(path, stream=False, source=None):
    resp = requests.Response()
    resp.status_code = 200
    resp._content_consumed = True
    # resp.headers['X-Fake-Source-Header'] = 'foobar'
    if path.endswith('0145/layer'):
        resp._content = "abcdef0123456789xxxxxx=-//"
    elif path.endswith('0145/json'):
        resp._content = ('{"id": "cafebabe0145","created":"2014-02-03T16:47:06'
                         '.615279788Z"}')
    elif path.endswith('0145/ancestry'):
        resp._content = '["cafebabe0145"]'
    elif path.endswith('test/tags'):
        resp._content = '{"latest": "cafebabe0145", "0.1.2": "cafebabe0145"}'
    else:
        resp.status_code = 404

    return resp


class TestMirrorDecorator(base.TestCase):
    def setUp(self):
        self.cfg = config.load()
        self.cfg._config['mirroring'] = {
            'source': 'https://registry.mock'
        }

    def tearDown(self):
        del self.cfg._config['mirroring']

    def test_config_tampering(self):
        self.assertEqual(self.cfg.mirroring.source,
                         'https://registry.mock')

    def test_is_mirror(self):
        self.assertEqual(mirroring.is_mirror(), True)

    @mock.patch('docker_registry.lib.mirroring.lookup_source',
                mock_lookup_source)
    def test_source_lookup(self):
        resp = self.http_client.get('/v1/images/cafebabe0145/layer')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, "abcdef0123456789xxxxxx=-//")

        resp_2 = self.http_client.get('/v1/images/cafebabe0145/json')
        self.assertEqual(resp_2.status_code, 200)
        # Note(dmp): unicode patch XXX not applied assume requests does the job
        json_data = json.loads(resp_2.data)
        assert 'id' in json_data
        assert 'created' in json_data
        self.assertEqual(json_data['id'], 'cafebabe0145')

        resp_3 = self.http_client.get('/v1/images/cafebabe0145/ancestry')
        self.assertEqual(resp_3.status_code, 200)
        # Note(dmp): unicode patch XXX not applied assume requests does the job
        json_data_2 = json.loads(resp_3.data)
        self.assertEqual(len(json_data_2), 1)
        self.assertEqual(json_data_2[0], 'cafebabe0145')

        resp_4 = self.http_client.get('/v1/images/doe587e8157/json')
        self.assertEqual(resp_4.status_code, 404)

    @mock.patch('docker_registry.lib.mirroring.lookup_source',
                mock_lookup_source)
    def test_source_lookup_tag(self):
        resp = self.http_client.get('/v1/repositories/testing/test/tags')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.data,
            '{"latest": "cafebabe0145", "0.1.2": "cafebabe0145"}'
        )

        resp_2 = self.http_client.get('/v1/repositories/testing/bogus/tags')
        self.assertEqual(resp_2.status_code, 404)
