# -*- coding: utf-8 -*-

"""Index backends for the search endpoint
"""

import importlib

from docker_registry.core import exceptions

from .. import config
from .. import signals

__all__ = ['load']


class Index (object):
    """A backend for the search endpoint

    The backend can use .walk_storage to generate an initial index,
    ._handle_repository_* to stay up to date with registry changes,
    and .results to respond to queries.
    """
    def __init__(self):
        signals.repository_created.connect(self._handle_repository_created)
        signals.repository_updated.connect(self._handle_repository_updated)
        signals.repository_deleted.connect(self._handle_repository_deleted)

    def _walk_storage(self, store):
        """Iterate through repositories in storage

        This helper is useful for building an initial database for
        your search index.  Yields dictionaries:

          {'name': name, 'description': description}
        """
        try:
            namespace_paths = list(
                store.list_directory(path=store.repositories))
        except exceptions.FileNotFoundError:
            namespace_paths = []
        for namespace_path in namespace_paths:
            namespace = namespace_path.rsplit('/', 1)[-1]
            try:
                repository_paths = list(
                    store.list_directory(path=namespace_path))
            except exceptions.FileNotFoundError:
                repository_paths = []
            for path in repository_paths:
                repository = path.rsplit('/', 1)[-1]
                name = '{0}/{1}'.format(namespace, repository)
                description = None  # TODO(wking): store descriptions
                yield({'name': name, 'description': description})

    def _handle_repository_created(
            self, sender, namespace, repository, value):
        pass

    def _handle_repository_updated(
            self, sender, namespace, repository, value):
        pass

    def _handle_repository_deleted(self, sender, namespace, repository):
        pass

    def results(self, search_term):
        """Return a list of results matching search_term

        The list elements should be dictionaries:

          {'name': name, 'description': description}
        """
        raise NotImplementedError('results method for {0!r}'.format(self))


def load(kind=None):
    """Returns an Index instance according to the configuration."""
    cfg = config.load()
    if not kind:
        kind = cfg.search_backend.lower()
    if kind == 'sqlalchemy':
        from . import db
        return db.SQLAlchemyIndex()
    try:
        module = importlib.import_module(kind)
    except ImportError:
        pass
    else:
        return module.Index()
    raise NotImplementedError('Unknown index type {0!r}'.format(kind))
