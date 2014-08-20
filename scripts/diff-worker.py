#!/usr/bin/env python

import argparse  # noqa

import logging
import os

import redis

from docker_registry.lib import layers
from docker_registry.lib import rlock
from docker_registry.lib import rqueue
import docker_registry.storage as storage

store = storage.load()

redis_default_host = os.environ.get(
    'DOCKER_REDIS_1_PORT_6379_TCP_ADDR',
    '0.0.0.0')
redis_default_port = int(os.environ.get(
    'DOCKER_REDIS_1_PORT_6379_TCP_PORT',
    '6379'))

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def get_parser():
    parser = argparse.ArgumentParser(
        description="Daemon for computing layer diffs"
    )
    parser.add_argument(
        "--rhost", default=redis_default_host, dest="redis_host",
        help="Host of redis instance to listen to",
    )
    parser.add_argument(
        "--rport", default=redis_default_port, dest="redis_port", type=int,
        help="Port of redis instance to listen to",
    )
    parser.add_argument(
        "-d", "--database", default=0, dest="redis_db",
        type=int, metavar="redis_db",
        help="Redis database to connect to",
    )
    parser.add_argument(
        "-p", "--password", default=None, metavar="redis_pw", dest="redis_pw",
        help="Redis database password",
    )
    return parser


def get_redis_connection(options):
    redis_conn = redis.StrictRedis(
        host=options.redis_host,
        port=options.redis_port,
        db=options.redis_db,
        password=options.redis_pw,
    )
    return redis_conn


def handle_request(layer_id, redis_conn):
    '''handler for any item pulled from worker job queue

    This handler is called every time the worker is able to pop a message
    from the job queue filled by the registry. The worker blocks until a
    message is available. This handler will then attempt to aquire a lock
    for the provided layer_id and if successful, process a diff for the
    layer.

    If the lock for this layer_id has already been aquired for this layer
    the worker will immediately timeout to block for another request.
    '''
    try:
        # this with-context will attempt to establish a 5 minute lock
        # on the key for this layer, immediately passing on LockTimeout
        # if one isn't availble
        with rlock.Lock(redis_conn,
                        "diff-worker-lock",
                        layer_id,
                        expires=60 * 5):
            # first check if a cached result is already available. The registry
            # already does this, but hey.
            diff_data = layers.get_image_diff_cache(layer_id)
            if not diff_data:
                log.info("Processing diff for %s" % layer_id)
                layers.get_image_diff_json(layer_id)
    except rlock.LockTimeout:
        log.info("Another worker is processing %s. Skipping." % layer_id)

if __name__ == '__main__':
    parser = get_parser()
    options = parser.parse_args()
    redis_conn = get_redis_connection(options)
    # create a bounded queue holding registry requests for diff calculations
    queue = rqueue.CappedCollection(redis_conn, "diff-worker", 1024)
    # initialize worker factory with the queue and redis connection
    worker_factory = rqueue.worker(queue, redis_conn)
    # create worker instance with our handler
    worker = worker_factory(handle_request)
    log.info("Starting worker...")
    worker()
