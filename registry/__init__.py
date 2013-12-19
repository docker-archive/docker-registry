# -*- coding: utf-8 -*-
# flake8: noqa

from .app import app
from .tags import *
from .images import *
from .status import *

import config

cfg = config.load()
if cfg.standalone is not False:
    # If standalone mode is enabled (default), load the fake Index routes
    from .index import *
