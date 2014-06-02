# -*- coding: utf-8 -*-

import os

__all__ = ['source']

_DEFAULT = {
    'REGISTRY_PORT': 5000,
    'REGISTRY_HOST': '0.0.0.0',
    'SETTINGS_FLAVOR': 'dev',
    'GUNICORN_WORKERS': 4,
    'GUNICORN_GRACEFUL_TIMEOUT': 3600,
    'GUNICORN_SILENT_TIMEOUT': 3600
}


def source(key, override=None):
    return os.environ.get(key, _DEFAULT[key] if key in _DEFAULT else override)
