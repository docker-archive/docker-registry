# -*- coding: utf-8 -*-

from __future__ import print_function

# this must happen before anything else
import gevent.monkey
gevent.monkey.patch_all()

from argparse import ArgumentParser  # noqa
from argparse import RawTextHelpFormatter  # noqa
import distutils.spawn
import os
import sys

from .app import app  # noqa
from .tags import *  # noqa
from .images import *  # noqa
from .lib import config
from .status import *  # noqa
from .search import *  # noqa

cfg = config.load()
if cfg.standalone is not False:
    # If standalone mode is enabled (default), load the fake Index routes
    from .index import *  # noqa


DESCRIPTION = """run the docker-registry with gunicorn, honoring the following
environment variables:

GUNICORN_WORKERS: number of worker processes gunicorn should start
REGISTRY_PORT: TCP port to bind to on all ipv4 addresses; default is 5000
GUNICORN_GRACEFUL_TIMEOUT: timeout in seconds for graceful worker restart
GUNiCORN_SILENT_TIMEOUT: timeout in seconds for restarting silent workers
"""


def run_gunicorn():
    """Exec gunicorn with our wsgi app.

    Settings are taken from environment variables as listed in the help text.
    This is intended to be called as a console_script entry point.
    """

    # this only exists to provide help/usage text
    parser = ArgumentParser(description=DESCRIPTION,
                            formatter_class=RawTextHelpFormatter)
    parser.parse_args()

    workers = os.environ.get('GUNICORN_WORKERS', '4')
    port = os.environ.get('REGISTRY_PORT', '5000')
    graceful_timeout = os.environ.get('GUNICORN_GRACEFUL_TIMEOUT', '3600')
    silent_timeout = os.environ.get('GUNICORN_SILENT_TIMEOUT', '3600')

    address = '0.0.0.0:{0}'.format(port)

    gunicorn_path = distutils.spawn.find_executable('gunicorn')
    if gunicorn_path is None:
        print('error: gunicorn executable not found', file=sys.stderr)
        sys.exit(1)

    os.execl(gunicorn_path, 'gunicorn', '--access-logfile', '-', '--debug',
             '--max-requests', '100', '--graceful-timeout', graceful_timeout,
             '-t', silent_timeout, '-k', 'gevent', '-b', address,
             '-w', workers, 'docker_registry.wsgi:application')
