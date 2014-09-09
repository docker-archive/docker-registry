# -*- coding: utf-8 -*-

import platform
import sys

from . import toolkit
from .extras import bugsnag
from .extras import cors
from .lib import config
from .server import __version__
import flask

from .lib import mirroring  # noqa

app = flask.Flask('docker-registry')


@app.route('/_ping')
@app.route('/v1/_ping')
def ping():
    headers = {
        'X-Docker-Registry-Standalone': 'mirror' if mirroring.is_mirror()
                                        else (cfg.standalone is True)
    }
    infos = {}
    if cfg.debug:
        # Versions
        versions = infos['versions'] = {}
        headers['X-Docker-Registry-Config'] = cfg.flavor

        for name, module in sys.modules.items():
            if name.startswith('_'):
                continue
            try:
                version = module.__version__
            except AttributeError:
                continue
            versions[name] = version
        versions['python'] = sys.version

        # Hosts infos
        infos['host'] = platform.uname()
        infos['launch'] = sys.argv

    return toolkit.response(infos, headers=headers)


@app.route('/')
def root():
    return toolkit.response(cfg.issue)
