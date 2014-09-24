#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from .server import env

_new_relic_ini = env.source('NEW_RELIC_INI')
if _new_relic_ini:
    try:
        import newrelic.agent
        newrelic.agent.initialize(
            _new_relic_ini,
            env.source('NEW_RELIC_STAGE'))
    except Exception as e:
        raise(Exception('Failed to init new relic agent %s' % e))

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
