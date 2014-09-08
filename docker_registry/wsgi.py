#!/usr/bin/env python
# -*- coding: utf-8 -*-

# only needed if not using gunicorn gevent
if __name__ == '__main__':
    import gevent.monkey
    gevent.monkey.patch_all()

# start new relic if instructed to do so
from .extras import newrelic
from .server import env
newrelic.boot(env.source('NEW_RELIC_INI'), env.source('NEW_RELIC_STAGE'))

from .extensions import factory
factory.boot()

import logging

from .app import app  # noqa
from .tags import *  # noqa
from .images import *  # noqa
from .lib import config

cfg = config.load()

if cfg.search_backend:
    from .search import *  # noqa

if cfg.standalone:
    # If standalone mode is enabled, load the fake Index routes
    from .index import *  # noqa

if __name__ == '__main__':
    host = env.source('REGISTRY_HOST')
    port = env.source('REGISTRY_PORT')
    app.debug = cfg.debug
    app.run(host=host, port=port)
else:
    level = cfg.loglevel.upper()
    if not hasattr(logging, level):
        level = 'INFO'
    level = getattr(logging, level)
    app.logger.setLevel(level)
    stderr_logger = logging.StreamHandler()
    stderr_logger.setLevel(level)
    stderr_logger.setFormatter(
        logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
    app.logger.addHandler(stderr_logger)
    application = app
