import functools
import logging
import os
import redis
import sys

cfg_path = os.path.realpath('lib')
sys.path.append(cfg_path)

import config

# Default options
redis_opts = {
    'host': 'localhost',
    'port': 6380,
    'db': 0,
    'password': None,
}
redis_conn = None


def init():
    global redis_conn, cache_prefix
    cfg = config.load()
    cache = cfg.bandwidth_cache
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


def put(f=None, time=None):
    if f is not None:
        @functools.wraps(f)
        def wrapper(*args):
            content = args[-1]
            key = args[-2]
            redis_conn.setex(key, time, content)  # time in seconds
            return f(*args)
        if redis_conn is None:
            return f
        return wrapper
    else:
        def partial_put(f):
            return put(f, time)
        return partial_put


def get(f):
    @functools.wraps(f)
    def wrapper(*args):
        key = args[-1]
        logging.info(key)
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
        redis_conn.delete(key)
        return f(*args)
    if redis_conn is None:
        return f
    return wrapper


init()
