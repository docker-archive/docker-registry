#!/bin/sh
# Right now, tox is unoperable due to namespace / egg / pip hell mess
# Given we don't use tox anyhow, this below does exactly the same thing (and works)
# Note that you have to install deps yourself though
SETTINGS_FLAVOR=test DOCKER_REGISTRY_CONFIG=config_test.yml PYTHONPATH=test coverage run -m unittest discover -s test
