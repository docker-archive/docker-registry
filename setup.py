#!/usr/bin/env python
# -*- coding: utf-8 -*-

try:
    import setuptools
except ImportError:
    import distutils.core as setuptools

import sys

ver = sys.version_info

# XXX as ugly as this looks, namespaces break terribly otherwise
filename = './docker_registry/server/__init__.py'
exec(compile(open(filename, 'rb').read(), filename, 'exec'))

requirements_txt = open('./requirements/main.txt')
requirements = [line for line in requirements_txt]

if ver[0] == 2:
    # Python 2 requires lzma backport
    requirements.insert(0, 'backports.lzma>=0.0.2')
    if ver[1] <= 6:
        # Python 2.6 requires additional libraries
        requirements.insert(0, 'argparse>=1.2.1')
        requirements.insert(0, 'importlib>=1.0.3')

# Require core (the reason this is out of req.txt is to ease tox)
requirements.insert(0, 'docker-registry-core>=2,<3')

# Explicit packages list to avoid setup_tools funkyness
packages = ['docker_registry',
            'docker_registry.drivers',
            'docker_registry.server',
            'docker_registry.lib',
            'docker_registry.storage',
            'docker_registry.lib.index']

namespaces = ['docker_registry', 'docker_registry.drivers']

package_data = {'docker_registry': ['../config/*']}


setuptools.setup(
    name=__title__,  # noqa
    version=__version__,  # noqa
    author=__author__,  # noqa
    author_email=__email__,  # noqa
    maintainer=__maintainer__,  # noqa
    maintainer_email=__email__,  # noqa
    url=__url__,  # noqa
    description=__description__,  # noqa
    download_url=__download__,  # noqa
    long_description=open('./README.md').read(),
    namespace_packages=namespaces,
    packages=packages,
    package_data=package_data,
    entry_points={
        'console_scripts': [
            'docker-registry = docker_registry.run:run_gunicorn'
        ]
    },

    classifiers=['Development Status :: 4 - Beta',
                 'Intended Audience :: Developers',
                 # 'Programming Language :: Python :: 2.6',
                 'Programming Language :: Python :: 2.7',
                 # 'Programming Language :: Python :: 3.2',
                 # 'Programming Language :: Python :: 3.3',
                 # 'Programming Language :: Python :: 3.4',
                 'Programming Language :: Python :: Implementation :: CPython',
                 'Operating System :: OS Independent',
                 'Topic :: Utilities',
                 'License :: OSI Approved :: Apache Software License'],
    platforms=['Independent'],
    license=open('./LICENSE').read(),
    zip_safe=False,
    test_suite='nose.collector',
    install_requires=requirements,
    tests_require=open('./requirements/test.txt').read(),
    extras_require={
        'bugsnag': ['bugsnag>=2.0,<2.1'],
        'newrelic': ['newrelic>=2.22,<2.23'],
    }
)
