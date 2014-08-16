import unittest

import mock

from docker_registry.lib import index


class TestIndex(unittest.TestCase):

    def setUp(self):
        self.index = index.Index()

    def test_cover_passed_methods(self):
        self.index._handle_repository_created(None, None, None, None)
        self.index._handle_repository_updated(None, None, None, None)
        self.index._handle_repository_deleted(None, None, None)

    def test_results(self):
        self.assertRaises(NotImplementedError, self.index.results, None)


class TestLoad(unittest.TestCase):

    @mock.patch('docker_registry.lib.config.load')
    def test_search_backend(self, load):
        load.return_value = mock.MagicMock(search_backend='x')
        self.assertRaises(NotImplementedError, index.load)
