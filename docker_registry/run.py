# -*- coding: utf-8 -*-

from __future__ import print_function

# this must happen before anything else
import gevent.monkey
gevent.monkey.patch_all()

from argparse import ArgumentParser  # noqa
from argparse import RawTextHelpFormatter  # noqa
import distutils.spawn
import getpass
import logging
import os
import sys

from .app import app  # noqa
from .tags import *  # noqa
from .images import *  # noqa
from .lib import config
from .server import env
from .status import *  # noqa
from .search import *  # noqa

cfg = config.load()
if cfg.standalone:
    # If standalone mode is enabled, load the fake Index routes
    from .index import *  # noqa


logger = logging.getLogger(__name__)

DESCRIPTION = """run the docker-registry with gunicorn, honoring the following
environment variables:
REGISTRY_HOST: TCP host or ip to bind to; default is 0.0.0.0
REGISTRY_PORT: TCP port to bind to; default is 5000
GUNICORN_WORKERS: number of worker processes gunicorn should start
GUNICORN_GRACEFUL_TIMEOUT: timeout in seconds for graceful worker restart
GUNICORN_SILENT_TIMEOUT: timeout in seconds for restarting silent workers
GUNICORN_USER: unix user to downgrade priviledges to
GUNICORN_GROUP: unix group to downgrade priviledges to
GUNICORN_ACCESS_LOG_FILE: File to log access to
GUNICORN_ERROR_LOG_FILE: File to log errors to
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

    gunicorn_path = distutils.spawn.find_executable('gunicorn')
    if not gunicorn_path:
        print('error: gunicorn executable not found', file=sys.stderr)
        sys.exit(1)

    address = '%s:%s' % (
        env.source('REGISTRY_HOST'),
        env.source('REGISTRY_PORT')
    )

    args = [
        gunicorn_path, 'gunicorn',
        '--access-logfile', env.source('GUNICORN_ACCESS_LOG_FILE'),
        '--error-logfile', env.source('GUNICORN_ERROR_LOG_FILE'),
        '--debug',
        '--max-requests', '100',
        '-k', 'gevent',
        '--graceful-timeout', env.source('GUNICORN_GRACEFUL_TIMEOUT'),
        '-t', env.source('GUNICORN_SILENT_TIMEOUT'),
        '-w', env.source('GUNICORN_WORKERS'),
        '-b', address,
    ] + env.source('GUNICORN_OPTS') + [
        'docker_registry.wsgi:application'
    ]

    user = env.source('GUNICORN_USER')
    group = env.source('GUNICORN_GROUP')
    if user or group:
        if getpass.getuser() == 'root':
            if user:
                logger.info('Downgrading privs to user %s' % user)
                args.append('-u')
                args.append(user)

            if group:
                logger.info('Downgrading privs to group %s' % user)
                args.append('-g')
                args.append(group)
        else:
            logger.warn('You asked we drop priviledges, but we are not root!')

    # Stringify all args
    for (k, v) in enumerate(args):
        args[k] = str(v)
    os.execl(*args)
