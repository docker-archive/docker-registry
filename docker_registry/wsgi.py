#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from .extras import newrelic
from .server import env
newrelic.boot(env.source('NEW_RELIC_INI'), env.source('NEW_RELIC_STAGE'))

from .extensions import factory
factory.boot()
from .run import app

if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    host = env.source('REGISTRY_HOST')
    port = env.source('REGISTRY_PORT')
    app.debug = True
    app.run(host=host, port=port)
else:
    # For uwsgi
    app.logger.setLevel(logging.INFO)
    stderr_logger = logging.StreamHandler()
    stderr_logger.setLevel(logging.INFO)
    stderr_logger.setFormatter(
        logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
    app.logger.addHandler(stderr_logger)

    application = app
