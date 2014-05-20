#!/usr/bin/env python
# -*- coding: utf-8 -*-

try:
    import setuptools
except ImportError:
    import distutils.core as setuptools

import sys

requirements_txt = open('./requirements.txt')
requirements = [line for line in requirements_txt]

ver = sys.version_info

if ver[0] == 2:
    requirements.insert(0, 'backports.lzma>=0.0.2')
    if ver[1] <= 6:
        requirements.insert(0, 'argparse>=1.2.1')
        requirements.insert(0, 'importlib>=1.0.3')

packages = ['docker_registry',
            'docker_registry.drivers',
            'docker_registry.lib',
            'docker_registry.storage',
            'docker_registry.lib.index']

setuptools.setup(
    name='docker-registry',
    # TODO: Load the version programatically, which is currently available in
    #       docker_registry.app. This is not possible yet because importing
    #       causes config files to be loaded
    version='0.7.0',
    description='Registry server for Docker',
    long_description=open('README.md').read(),
    namespace_packages=['docker_registry', 'docker_registry.drivers'],
    packages=packages,
    license=open('LICENSE').read(),
    author='Docker Registry Contributors',
    author_email='docker-dev@googlegroups.com',
    url='https://github.com/dotcloud/docker-registry',
    install_requires=requirements,
    classifiers=(
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
    ),
    platforms=['Independent'],
    package_data={'docker_registry': ['../config/*']},
    entry_points={
        'console_scripts': [
            'docker-registry = docker_registry.run:run_gunicorn'
        ]
    },
    zip_safe=False,
    tests_require=open('./tests/requirements.txt').read(),
    test_suite='nose.collector'
)
