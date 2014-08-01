# -*- coding: utf-8 -*-

import logging
import redis

from docker_registry.core import lru

from . import config

logger = logging.getLogger(__name__)

redis_conn = None
cache_prefix = None

cfg = config.load()


def init():
    enable_redis_cache(cfg.cache, cfg.storage_path)
    enable_redis_lru(cfg.cache_lru, cfg.storage_path)


def enable_redis_cache(cache, path):
    global redis_conn, cache_prefix
    if not cache or not cache.host:
        logger.warn('Cache storage disabled!')
        return

    logger.info('Enabling storage cache on Redis')
    logger.info(
        'Redis host: {0}:{1} (db{2})'.format(cache.host, cache.port, cache.db)
    )
    redis_conn = redis.StrictRedis(
        host=cache.host,
        port=int(cache.port),
        db=int(cache.db),
        password=cache.password
    )
    cache_prefix = 'cache_path:{0}'.format(path or '/')


def enable_redis_lru(cache, path):
    if not cache or not cache.host:
        logger.warn('LRU cache disabled!')
        return
    logger.info('Enabling lru cache on Redis')
    logger.info(
        'Redis lru host: {0}:{1} (db{2})'.format(cache.host, cache.port,
                                                 cache.db)
    )
    lru.init(
        host=cache.host,
        port=cache.port,
        db=cache.db,
        password=cache.password,
        path=path or '/'
    )

init()
