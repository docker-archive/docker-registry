# -*- coding: utf-8 -*-

import os
import yaml

__all__ = ['source']

_DEFAULT = {
    'REGISTRY_PORT': '5000',
    'REGISTRY_HOST': '0.0.0.0',
    'SETTINGS_FLAVOR': 'dev',
    'GUNICORN_WORKERS': '4',
    'GUNICORN_GRACEFUL_TIMEOUT': '3600',
    'GUNICORN_SILENT_TIMEOUT': '3600',
    'GUNICORN_ACCESS_LOG_FILE': '"-"',
    'GUNICORN_ERROR_LOG_FILE': '"-"',
    'GUNICORN_OPTS': '[]',
    'NEW_RELIC_INI': '',
    'NEW_RELIC_STAGE': 'dev'
}


def source(key, override=''):
    # Using yaml gives us proper typage
    return yaml.load(
        os.environ.get(key, _DEFAULT[key] if key in _DEFAULT else override))
