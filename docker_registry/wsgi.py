#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Needs to happen before anything else, but only needed if not using gevent
if __name__ == '__main__':
    import gevent.monkey
    gevent.monkey.patch_all()

# start new relic if instructed to do so
from .extensions import factory
from .extras import newrelic
from .server import env
newrelic.boot(env.source('NEW_RELIC_CONFIG_FILE'),
              env.source('NEW_RELIC_LICENSE_KEY'))
factory.boot()

from .server import log

# Start new relic if instructed to do so
newrelic.boot(env.source('NEW_RELIC_INI'), env.source('NEW_RELIC_STAGE'))

# Get configuration
from .lib import config
cfg = config.load()

# Setup logging
log.setup(cfg.loglevel, cfg.email_exceptions)

# Get the main app and the other routes
from .app import app
from . import images  # noqa
from . import tags  # noqa
# If search is enabled, add the route
if cfg.search_backend:
    from . import search  # noqa
# If standalone mode is enabled, load the fake Index routes
if cfg.standalone:
    from . import index  # noqa

# Optional bugsnag support
bugsnag.boot(app, cfg.bugsnag, cfg.flavor, __version__)

# Optional cors support
cors.boot(app, cfg.cors)

# Run standalone, or under gunicorn
if __name__ == '__main__':
    app.run(host=env.source('REGISTRY_HOST'), port=env.source('REGISTRY_PORT'))
else:
    application = app
