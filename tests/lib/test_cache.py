import mock

from docker_registry.lib import cache
from tests.base import TestCase


class TestCache(TestCase):

    def setUp(self):
        self.cache = mock.MagicMock(
            host='localhost', port=1234, db=0, password='pass')

    def tearDown(self):
        cache.redis_conn = None
        cache.cache_prefix = None

    @mock.patch.object(cache, 'logger')
    def test_enable_redis_cache(self, logger):
        self.assertEqual(cache.redis_conn, None)
        self.assertEqual(cache.cache_prefix, None)
        cache.enable_redis_cache(None, None)
        self.assertEqual(logger.warn.call_count, 1)

        cache.enable_redis_cache(self.cache, None)
        self.assertTrue(cache.redis_conn is not None)
        self.assertEqual(type(cache.redis_conn), cache.redis.StrictRedis)
        self.assertTrue(cache.cache_prefix is not None)
        self.assertEqual(cache.cache_prefix, 'cache_path:/')

        cache.enable_redis_cache(self.cache, 'test')
        self.assertEqual(cache.cache_prefix, 'cache_path:test')

    @mock.patch.object(cache, 'logger')
    @mock.patch.object(cache.lru, 'init')
    def test_enable_redis_lru(self, lru_init, logger):
        cache.enable_redis_lru(None, None)
        self.assertEqual(logger.warn.call_count, 1)

        cache.enable_redis_lru(self.cache, None)
        self.assertEqual(logger.info.call_count, 2)
        lru_init.assert_called_once_with(
            host=self.cache.host, port=self.cache.port, db=self.cache.db,
            password=self.cache.password, path='/')

        lru_init.reset_mock()
        path = 'test'
        cache.enable_redis_lru(self.cache, path)
        lru_init.assert_called_once_with(
            host=self.cache.host, port=self.cache.port, db=self.cache.db,
            password=self.cache.password, path=path)
