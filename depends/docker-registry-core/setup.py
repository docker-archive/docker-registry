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

import sys

import docker_registry.core as core

if sys.version_info < (2, 6):
    raise Exception("Docker registry requires Python 2.6 or higher.")

requirements_txt = open('./requirements/main.txt')
requirements = [line for line in requirements_txt]

ver = sys.version_info

# 2.6 native json raw_decode doesn't fit the bill, so add simple to our req
if ver[0] == 2 and ver[1] <= 6:
    requirements.insert(0, 'simplejson>=2.0.9')

# d = 'https://github.com/dotcloud/docker-registry-core/archive/master.zip'

setuptools.setup(
    name=core.__title__,
    version=core.__version__,
    author=core.__author__,
    author_email=core.__email__,
    maintainer=core.__maintainer__,
    maintainer_email=core.__email__,
    keywords="docker registry core",
    url='https://github.com/dotcloud/docker-registry',
    description="Docker registry core package",
    long_description=open('./README.md').read(),
    # download_url=d,
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
    # XXX setuptools breaks terribly when mixing namespaces and package_dir
    # TODO must report this to upstream
    # package_dir={'docker_registry': 'lib'},
    packages=['docker_registry', 'docker_registry.core',
              'docker_registry.drivers', 'docker_registry.testing'],
    install_requires=requirements,
    zip_safe=True,
    tests_require=open('./requirements/test.txt').read(),
    test_suite='nose.collector'
)
