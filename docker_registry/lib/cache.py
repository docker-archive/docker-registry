# -*- coding: utf-8 -*-

import logging

import redis

from docker_registry.core import lru

from . import config


# Default options

redis_conn = None
cache_prefix = None


def init():
    cfg = config.load()
    enable_redis_cache(cfg)
    enable_redis_lru(cfg)


def enable_redis_cache(cfg):
    global redis_conn, cache_prefix
    cache = cfg.cache
    if not cache:
        return

    logging.info('Enabling storage cache on Redis')
    if not isinstance(cache, dict):
        cache = {}
    redis_opts = {
        'host': 'localhost',
        'port': 6379,
        'db': 0,
        'password': None
    }
    for k, v in cache.iteritems():
        redis_opts[k] = v
    logging.info('Redis config: {0}'.format(redis_opts))
    redis_conn = redis.StrictRedis(host=redis_opts['host'],
                                   port=int(redis_opts['port']),
                                   db=int(redis_opts['db']),
                                   password=redis_opts['password'])
    cache_prefix = 'cache_path:{0}'.format(cfg.get('storage_path', '/'))


def enable_redis_lru(cfg):
    cache = cfg.cache_lru
    if not cache:
        return
    logging.info('Enabling lru cache on Redis')
    if not isinstance(cache, dict):
        cache = {}
    redis_opts = {
        'host': 'localhost',
        'port': 6379,
        'db': 0,
        'password': None
    }
    for k, v in cache.iteritems():
        redis_opts[k] = v

    logging.info('Redis lru config: {0}'.format(redis_opts))
    lru.init(
        host=redis_opts['host'],
        port=int(redis_opts['port']),
        db=int(redis_opts['db']),
        password=redis_opts['password'],
        path=cfg.get('storage_path', '/')
    )

init()
