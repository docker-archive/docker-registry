# -*- coding: utf-8 -*-
"""
docker_registry.core.lru
~~~~~~~~~~~~~~~~~~~~~~~~~~

Redis based LRU.
Can be activated or de-activated globally.
Drivers are largely encouraged to use it.
By default, doesn't run, until one calls init().
"""

import functools
import logging
import redis

logger = logging.getLogger(__name__)

redis_conn = None
cache_prefix = None


def init(enable=True,
         host='localhost', port=6379, db=0, password=None, path='/'):
    global redis_conn, cache_prefix
    if not enable:
        redis_conn = None
        return
    logging.info('Enabling storage cache on Redis')
    logging.info('Redis config: {0}'.format({
        'host': host,
        'port': port,
        'db': db,
        'password': password,
        'path': path
    }))
    redis_conn = redis.StrictRedis(host=host,
                                   port=int(port),
                                   db=int(db),
                                   password=password)
    cache_prefix = 'cache_path:{0}'.format(path)


def cache_key(key):
    return cache_prefix + key


def set(f):
    @functools.wraps(f)
    def wrapper(*args):
        content = args[-1]
        key = args[-2]
        key = cache_key(key)
        redis_conn.set(key, content)
        return f(*args)
    if redis_conn is None:
        return f
    return wrapper


def get(f):
    @functools.wraps(f)
    def wrapper(*args):
        key = args[-1]
        key = cache_key(key)
        content = redis_conn.get(key)
        if content is not None:
            return content
        # Refresh cache
        content = f(*args)
        if content is not None:
            redis_conn.set(key, content)
        return content
    if redis_conn is None:
        return f
    return wrapper


def remove(f):
    @functools.wraps(f)
    def wrapper(*args):
        key = args[-1]
        key = cache_key(key)
        redis_conn.delete(key)
        return f(*args)
    if redis_conn is None:
        return f
    return wrapper
