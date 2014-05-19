# -*- coding: utf-8 -*-

import logging

import redis

from docker_registry.core import lru

from . import config


# Default options

redis_opts = {
    'host': 'localhost',
    'port': 6379,
    'db': 0,
    'password': None
}
redis_conn = None
cache_prefix = None


def init():
    global redis_conn, cache_prefix
    cfg = config.load()
    cache = cfg.cache
    if not cache:
        return

    logging.info('Enabling storage cache on Redis')
    if not isinstance(cache, dict):
        cache = {}
    for k, v in cache.iteritems():
        redis_opts[k] = v
    logging.info('Redis config: {0}'.format(redis_opts))
    redis_conn = redis.StrictRedis(host=redis_opts['host'],
                                   port=int(redis_opts['port']),
                                   db=int(redis_opts['db']),
                                   password=redis_opts['password'])
    cache_prefix = 'cache_path:{0}'.format(cfg.get('storage_path', '/'))

    # Enable the LRU as well
    lru.init(
        host=redis_opts['host'],
        port=int(redis_opts['port']),
        db=int(redis_opts['db']),
        password=redis_opts['password'],
        path=cfg.get('storage_path', '/')
    )

init()
