# -*- coding: utf-8 -*-

import os

__all__ = ['source']

defined = {
    'REGISTRY_PORT': 5000,
    'REGISTRY_HOST': '0.0.0.0',
    'SETTINGS_FLAVOR': 'dev',
    'GUNICORN_WORKERS': 4,
    'GUNICORN_GRACEFUL_TIMEOUT': 3600,
    'GUNICORN_SILENT_TIMEOUT': 3600
}


def source(key, override=None):
    return os.environ.get(key, defined[key] if key in defined else override)
