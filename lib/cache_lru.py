import functools
import logging

import redis

import config


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
    cache = cfg.cache_lru
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


def cache_key(key):
    return cache_prefix + key


def put(f):
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

init()
