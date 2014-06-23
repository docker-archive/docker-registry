#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from .run import app
from .server import env


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
