#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import logging

root_path = os.path.abspath(os.path.dirname(__file__))
sys.path.append(os.path.join(root_path, 'lib'))

import registry


if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    port = int(os.environ.get('PORT_WWW', 5000))
    registry.app.debug = True
    registry.app.run(host='0.0.0.0', port=port)
    # Or you can run:
    # gunicorn --access-logfile - --log-level debug --debug -b 0.0.0.0:5000 -w 1 wsgi:application
else:
    # For uwsgi
    registry.app.logger.setLevel(logging.INFO)
    stderr_logger = logging.StreamHandler()
    stderr_logger.setLevel(logging.INFO)
    stderr_logger.setFormatter(
        logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
    registry.app.logger.addHandler(stderr_logger)
    application = registry.app
    # uwsgi
    app = application
