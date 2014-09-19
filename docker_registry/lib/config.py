# -*- coding: utf-8 -*-

import os

import rsa
import yaml

from docker_registry.core import compat
from docker_registry.core import exceptions


class Config(object):
    """A simple config class

     * gives properties access through either items or attributes
     * enforce types (thanks to yaml)
     * interpolate from ENV
    """

    def __init__(self, config=None):
        if config is None:
            config = {}
        if isinstance(config, compat.basestring):
            try:
                self._config = yaml.load(config)
            except Exception as e:
                # Failed yaml loading? Stop here!
                raise exceptions.ConfigError(
                    'Config is not valid yaml (%s): \n%s' % (e, config))
        else:
            # Config is kept as-is...
            self._config = config

    def __repr__(self):
        return repr(self._config)

    def __dir__(self):
        return self._config.keys()

    def keys(self):
        return self._config.keys()

    # Python 2.6 and below need this
    @property
    def __members__(self):
        return self._config.keys()

    @property
    def __methods__(self):
        return []

    def __getattr__(self, key):
        # Unset keys return None
        if key not in self._config:
            return None
            # raise exceptions.ConfigError("No such attribute: %s" % key)
        result = self._config[key]
        # Strings starting with `_env:' get evaluated
        if isinstance(
                result, compat.basestring) and result.startswith('_env:'):
            result = result.split(':', 2)
            varname = result[1]
            vardefault = '' if len(result) < 3 else result[2]
            try:
                result = yaml.load(os.environ.get(varname, vardefault))
            except Exception as e:
                raise exceptions.ConfigError(
                    'Config `%s` (value: `%s`) is not valid: %s' % (
                        varname, e, result))
        # Dicts are rewrapped inside a Config object
        if isinstance(result, dict):
            result = Config(result)
        return result

    def __getitem__(self, key):
        return getattr(self, key)

    def __contains__(self, key):
        return key in self._config


def _init():
    flavor = os.environ.get('SETTINGS_FLAVOR', 'dev')
    config_path = os.environ.get('DOCKER_REGISTRY_CONFIG', 'config.yml')

    if not os.path.isabs(config_path):
        config_path = os.path.join(os.path.dirname(__file__), '../../',
                                   'config', config_path)
    try:
        f = open(config_path)
    except Exception:
        raise exceptions.FileNotFoundError(
            'Heads-up! File is missing: %s' % config_path)

    conf = Config(f.read())
    if flavor:
        if flavor not in conf:
            raise exceptions.ConfigError(
                'The specified flavor (%s) is missing in your config file (%s)'
                % (flavor, config_path))
        conf = conf[flavor]
        conf.flavor = flavor

    if conf.privileged_key:
        try:
            f = open(conf.privileged_key)
        except Exception:
            raise exceptions.FileNotFoundError(
                'Heads-up! File is missing: %s' % conf.privileged_key)

        try:
            conf.privileged_key = rsa.PublicKey.load_pkcs1(f.read())
        except Exception:
            raise exceptions.ConfigError(
                'Key at %s is not a valid RSA key' % conf.privileged_key)

    if conf.index_endpoint:
        conf.index_endpoint = conf.index_endpoint.strip('/')

    return conf

_config = None


def load():
    global _config

    if not _config:
        _config = _init()

    return _config
