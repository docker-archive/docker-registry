#!/usr/bin/env python
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

try:
    import setuptools
except ImportError:
    import distutils.core as setuptools

import os
import re
import sys

import docker_registry.core as core

ver = sys.version_info

if ver < (2, 6):
    raise Exception("Docker registry requires Python 2.6 or higher.")

requirements_txt = open('./requirements/main.txt')
requirements = [line for line in requirements_txt]

# Using this will relax dependencies to semver major matching
if 'DEPS' in os.environ and os.environ['DEPS'].lower() == 'loose':
    loose = []
    for item in requirements:
        d = re.match(r'([^=]+)==([0-9]+)[.]([0-9]+)[.]([0-9]+)', item)
        if d:
            d = list(d.groups())
            name = d.pop(0)
            version = d.pop(0)
            item = '%s>=%s,<%s' % (name, int(version), int(version) + 1)
        loose.insert(0, item)
    requirements = loose

setuptools.setup(
    name=core.__title__,
    version=core.__version__,
    author=core.__author__,
    author_email=core.__email__,
    maintainer=core.__maintainer__,
    maintainer_email=core.__email__,
    keywords='docker registry core',
    url=core.__url__,
    description=core.__description__,
    long_description=open('./README.md').read(),
    download_url=core.__download__,
    classifiers=['Development Status :: 4 - Beta',
                 'Intended Audience :: Developers',
                 'Programming Language :: Python',
                 'Programming Language :: Python :: 2.6',
                 'Programming Language :: Python :: 2.7',
                 # 'Programming Language :: Python :: 3.2',
                 # 'Programming Language :: Python :: 3.3',
                 'Programming Language :: Python :: 3.4',
                 'Programming Language :: Python :: Implementation :: CPython',
                 # 'Programming Language :: Python :: Implementation :: PyPy',
                 'Operating System :: OS Independent',
                 'Topic :: Utilities',
                 'License :: OSI Approved :: Apache Software License'],
    platforms=['Independent'],
    license=open('./LICENSE').read(),
    namespace_packages=['docker_registry', 'docker_registry.drivers'],
    packages=['docker_registry', 'docker_registry.core',
              'docker_registry.drivers', 'docker_registry.testing'],
    install_requires=requirements,
    zip_safe=True,
    tests_require=open('./requirements/test.txt').read(),
    test_suite='nose.collector'
)
