# -*- coding: utf-8 -*-
# Copyright (c) 2014 Docker.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
