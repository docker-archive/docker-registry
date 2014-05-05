# -*- coding: utf-8 -*-
"""
docker-registry.exceptions
~~~~~~~~~~~~~~~~~~~~~

"""

__all__ = [
    "UnspecifiedError",
    "UsageError", "NotImplementedError", "FileNotFoundError", "ConfigError"
    # "WrongArgumentsError",
    # "ConnectionError", "UnreachableError", "MissingError", "BrokenError"
]


class UnspecifiedError(Exception):

    """Base class for all exceptions in docker-registry.
    """

    def __init__(self, *args, **kwargs):
        self.message = kwargs.pop('message', 'No details')
        super(UnspecifiedError, self).__init__(*args, **kwargs)


class UsageError(UnspecifiedError):

    """Exceptions related to use of the library."""


class NotImplementedError(UsageError):

    """Requested feature is not supported / not implemented."""


class FileNotFoundError(UsageError):

    """Requested (config) file not found."""


class ConfigError(UsageError):

    """Something in the configuration file is not ok."""


# class WrongArgumentsError(UsageError):

#     """Expected arguments not satisfied."""


# class ConnectionError(UnspecifiedError):

#     """Exceptions related to server/client operation."""


# class UnreachableError(ConnectionError):

#     """The requested server is not reachable."""


# class MissingError(ConnectionError):

#     """The requested ressource is not to be found on the server."""


# class BrokenError(ConnectionError):

#     """Something died on our hands, that the server couldn't digest..."""
