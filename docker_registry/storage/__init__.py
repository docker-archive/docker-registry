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

    store = engine.fetch(kind)(None, config=cfg)

    # if kind == 'swift':
    #     store = engine.fetch(kind)(None, config=cfg)
    # elif kind == 'file':
    #     store = engine.fetch(kind)(None, config=cfg)

    # if kind == 's3':
    #     import s3
    #     store = s3.S3Storage(cfg)
    # elif kind == 'glance':
    #     import glance
    #     store = glance.GlanceStorage(cfg)
    # elif kind == 'elliptics':
    #     import ellipticsbackend
    #     store = ellipticsbackend.EllipticsStorage(cfg)
    # elif kind == 'gcs':
    #     import gcs
    #     store = gcs.GSStorage(cfg)
    # else:
    #     raise ValueError('Not supported storage \'{0}\''.format(kind))
    _storage[kind] = store
    return store
