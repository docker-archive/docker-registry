# -*- coding: utf-8 -*-

import docker_registry.core.driver as engine

import tempfile

from ..lib import config


__all__ = ['load']


def temp_store_handler():
    tmpf = tempfile.TemporaryFile()

    def fn(buf):
        tmpf.write(buf)

    return tmpf, fn


_storage = {}


def load(kind=None):
    """Returns the right storage class according to the configuration."""
    global _storage
    cfg = config.load()
    if not kind:
        kind = cfg.storage.lower()
    if kind == 'local':
        kind = 'file'
    if kind in _storage:
        return _storage[kind]

    _storage[kind] = engine.fetch(kind)(
        path=cfg.storage_path,
        config=cfg)

    return _storage[kind]
