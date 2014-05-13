#!/usr/bin/env python
# -*- coding: utf-8 -*-

try:
    import setuptools
except ImportError:
    import distutils.core as setuptools

import sys

from docker_registry import core  # noqa

if sys.version_info < (2, 6):
    raise Exception("Docker registry requires Python 2.6 or higher.")

requirements_txt = open('./requirements.txt')
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
    url='https://github.com/dotclout/docker-registry',
    description="Docker registry core package",
    long_description=open('./README').read(),
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
    tests_require=open('./tests/requirements.txt').read(),
    test_suite='nose.collector'
)
