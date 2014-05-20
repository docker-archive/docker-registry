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
docker_registry.core.compat
~~~~~~~~~~~~~~~~~~~~~~

This file defines a collection of properties to quickly identify what python
runtime/version we are working with, and handles the import of problematic
modules, hence hiding import gymnastics from other components.

Use imports from here to ensure portability.

Largely stolen from requests (http://docs.python-requests.org/en/latest/)
under Apache2 license
"""

import logging
import sys

__all__ = ['builtin_str', 'str', 'bytes', 'basestring', 'json', 'quote_plus',
           'StringIO']

logger = logging.getLogger(__name__)

# -------
# Pythons
# -------

_ver = sys.version_info

is_py2 = (_ver[0] == 2)
is_py3 = (_ver[0] == 3)

is_py26 = (is_py2 and _ver[1] == 6)
# is_py27 = (is_py2 and _ver[1] == 7)
# is_py30 = (is_py3 and _ver[1] == 0)
# is_py31 = (is_py3 and _ver[1] == 1)
# is_py32 = (is_py3 and _ver[1] == 2)
# is_py33 = (is_py3 and _ver[1] == 3)
# is_py34 = (is_py3 and _ver[1] == 4)

# ---------
# Platforms
# ---------

# _ver = sys.version.lower()

# is_pypy = ('pypy' in _ver)
# is_jython = ('jython' in _ver)
# is_ironpython = ('iron' in _ver)
# is_cpython = not any((is_pypy, is_jython, is_ironpython))

# is_windows = 'win32' in str(sys.platform).lower()
# is_linux = ('linux' in str(sys.platform).lower())
# is_osx = ('darwin' in str(sys.platform).lower())
# is_hpux = ('hpux' in str(sys.platform).lower())   # Complete guess.
# is_solaris = ('solar' in str(sys.platform).lower())   # Complete guess.

if is_py26:
    logger.debug("Old python! Using simplejson.")
    import simplejson as json  # noqa
else:
    import json  # noqa

# ---------
# Specifics
# ---------

if is_py2:
    logger.debug("This is python2")
    from urllib import quote_plus  # noqa

    builtin_str = str
    bytes = str
    str = unicode
    basestring = basestring
    # numeric_types = (int, long, float)

    from cStringIO import StringIO  # noqa

elif is_py3:
    logger.debug("This is python3")
    from urllib.parse import quote_plus  # noqa

    builtin_str = str
    str = str
    bytes = bytes
    basestring = (str, bytes)
    # numeric_types = (int, float)

    from io import BytesIO as StringIO  # noqa
