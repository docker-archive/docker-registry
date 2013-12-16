#!/usr/bin/env python

import time
import hashlib
import os
import sys
import argparse

import simplejson as json

import redis

root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(root_path)
sys.path.append(os.path.join(root_path, 'lib'))

import storage
import cache, rqueue, rlock
from registry import images

store = storage.load()

redis_default_host = os.environ.get('REDIS_PORT_6379_TCP_ADDR', '0.0.0.0')
redis_default_port = int(os.environ.get('REDIS_PORT_6379_TCP_PORT', '6379'))

def get_parser():
    parser = argparse.ArgumentParser(description="Daemon for computing layer diffs")
    parser.add_argument(
        "--rhost", default=redis_default_host, dest="redis_host",
        help = "Host of redis instance to listen to", 
    )
    parser.add_argument(
        "--rport", default=redis_default_port, dest="redis_port",
        help = "Port of redis instance to listen to", 
    )
    parser.add_argument(
        "-d", "--database", default=0, type=int, metavar="redis_db", dest="redis_db",
        help = "Redis database to connect to",
    )
    parser.add_argument(
        "-p", "--password", default=None, metavar="redis_pw", dest="redis_pw",
        help = "Redis database password",
    )
    return parser

def get_redis_connection(options):
    redis_conn = redis.StrictRedis(
        host = options.redis_host,
        port = options.redis_port,
        db = options.redis_db,
        password = options.redis_pw,
    )
    return redis_conn

def handle_request(image_id, redis_conn):
    with rlock.Lock(redis_conn, "diff-worker-lock", image_id, expires=60*10, timeout=60*5):
        print "Processing diff for %s" % image_id
        time.sleep(1)
        diff_data = images._get_image_diff(image_id)
        print diff_data

if __name__ == '__main__':
    parser = get_parser()
    options = parser.parse_args()
    redis_conn = get_redis_connection(options)
    queue = rqueue.CappedCollection(redis_conn, "diff-worker", 1024)
    worker = rqueue.worker(queue, redis_conn)
    print "Starting worker..."
    worker(handle_request)()
