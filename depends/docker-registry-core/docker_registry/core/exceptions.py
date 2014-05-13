# -*- coding: utf-8 -*-
"""
docker_registry.core.exceptions
~~~~~~~~~~~~~~~~~~~~~

Provide docker_registry exceptions to be used consistently in the drivers
and registry.
"""

__all__ = [
    "UnspecifiedError",
    "UsageError",
    "NotImplementedError", "FileNotFoundError", "WrongArgumentsError",
    "ConfigError",
    "ConnectionError",
    "UnreachableError", "MissingError", "BrokenError"
]


class UnspecifiedError(Exception):

    """Base class for all exceptions in docker_registry
    """

    def __init__(self, *args, **kwargs):
        self.message = kwargs.pop('message', 'No details')
        super(UnspecifiedError, self).__init__(*args, **kwargs)


class UsageError(UnspecifiedError):

    """Exceptions related to use of the library, like missing files,
    wrong argument type, etc.
    """


class NotImplementedError(UsageError):

    """The requested feature is not supported / not implemented."""


class FileNotFoundError(UsageError):

    """The requested (config) file is missing."""


class WrongArgumentsError(UsageError):

    """Expected arguments type not satisfied."""


class ConfigError(UsageError):

    """The provided configuration has problems."""


class ConnectionError(UnspecifiedError):

    """Network communication related errors all inherit this."""


class UnreachableError(ConnectionError):

    """The requested server is not reachable."""


class MissingError(ConnectionError):

    """The requested ressource is not to be found on the server."""


class BrokenError(ConnectionError):

    """Something died on our hands, that the server couldn't digest..."""
