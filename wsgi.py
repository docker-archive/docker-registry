#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os

import docker_registry


if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    port = int(os.environ.get('PORT_WWW', 5000))
    docker_registry.app.debug = True
    docker_registry.app.run(host='0.0.0.0', port=port)
    # Or you can run:
    # gunicorn --access-logfile - --log-level debug --debug -b 0.0.0.0:5000 \
    #  -w 1 wsgi:application
else:
    # For uwsgi
    docker_registry.app.logger.setLevel(logging.INFO)
    stderr_logger = logging.StreamHandler()
    stderr_logger.setLevel(logging.INFO)
    stderr_logger.setFormatter(
        logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
    docker_registry.app.logger.addHandler(stderr_logger)
    application = docker_registry.app
    # uwsgi
    app = application
