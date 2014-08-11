#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .server import env
import logging

_new_relic_ini = env.source('NEW_RELIC_INI')
if _new_relic_ini:
    try:
        import newrelic.agent
        newrelic.agent.initialize(
            _new_relic_ini,
            env.source('NEW_RELIC_STAGE'))
    except Exception as e:
        raise(Exception('Failed to init new relic agent %s' % e))

from .run import app

if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    host = env.source('REGISTRY_HOST')
    port = env.source('REGISTRY_PORT')
    app.debug = True
    app.run(host=host, port=port)
    # Or you can run:
    # gunicorn --access-logfile - --log-level debug --debug -b 0.0.0.0:5000 \
    #  -w 1 wsgi:application
else:
    # For uwsgi
    app.logger.setLevel(logging.INFO)
    stderr_logger = logging.StreamHandler()
    stderr_logger.setLevel(logging.INFO)
    stderr_logger.setFormatter(
        logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
    app.logger.addHandler(stderr_logger)

    application = app
