#!/usr/bin/env python

import os
import setuptools
import sys

_abs_dir = os.path.dirname(os.path.abspath(__file__))

desc_path = os.path.join(_abs_dir, 'README.md')
long_desc = open(desc_path).read()

requirements_txt = open('./requirements.txt')
requirements = [line for line in requirements_txt]

ver = sys.version_info

if ver[0] == 2:
    requirements.insert(0, 'backports.lzma>=0.0.2')

setuptools.setup(
    name='docker-registry',
    # TODO: Load the version programatically, which is currently available in
    #       docker_registry.app. This is not possible yet because importing
    #       causes config files to be loaded
    version='0.7.0',
    description='Registry server for Docker',
    long_description=long_desc,
    namespace_packages=['docker_registry', 'docker_registry.drivers'],
    packages=setuptools.find_packages(),
    license='Apache',
    author='Docker Registry Contributors',
    author_email='docker-dev@googlegroups.com',
    url='https://github.com/dotcloud/docker-registry',
    install_requires=requirements,
    classifiers=(
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
    ),
    entry_points={
        'console_scripts': [
            'docker-registry = docker_registry.run:run_gunicorn'
        ]
    }
)
