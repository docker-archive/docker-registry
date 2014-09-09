# -*- coding: utf-8 -*-

import platform
import sys

from . import toolkit
from .lib import config
import flask

app = flask.Flask('docker-registry')
cfg = config.load()


@app.route('/_ping')
@app.route('/v1/_ping')
def ping():
    # Both these are used by the docker engine to determine behavior
    headers = {
        'X-Docker-Registry-Standalone':
        'mirror' if cfg.mirroring and cfg.mirroring.source
        else cfg.standalone is True
    }
    infos = {}

    # If debugging, output a bunch of infos in the body
    if cfg.debug:
        # Config flavor
        headers['X-Docker-Registry-Config'] = cfg.flavor

        # Versions
        versions = infos['versions'] = {}
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
