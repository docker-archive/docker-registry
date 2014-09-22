# -*- coding: utf-8 -*-

import pkg_resources


def boot():
    for ep in pkg_resources.iter_entry_points('docker_registry.extensions'):
        ep.load()


def list():
    return list(pkg_resources.iter_entry_points('docker_registry.extensions'))
