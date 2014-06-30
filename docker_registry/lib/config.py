# -*- coding: utf-8 -*-

import os
import rsa
import yaml

from docker_registry.core import compat
from docker_registry.core import exceptions


class Config(object):
    """A simple config class that:
     * gives properties access through either items or attributes
     * enforce types (thanks to yaml)
     * interpolate from ENV
    """

    def __init__(self, config=''):
        try:
            # Config is kept as-is...
            self._config = config
            # ... save Strings, that are yaml loaded
            if isinstance(config, compat.basestring):
                self._config = yaml.load(config)
        except Exception as e:
            # Failed yaml loading? Stop here!
            raise exceptions.ConfigError(
                'Config is not valid yaml (%s): \n%s' % (e, config))

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


_config = None


def load():
    global _config
    if _config is not None:
        return _config

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

    _config = Config(f.read())
    if flavor:
        _config = _config[flavor]
        _config.flavor = flavor

    if _config.privileged_key:
        try:
            f = open(_config.privileged_key)
        except Exception:
            raise exceptions.FileNotFoundError(
                'Heads-up! File is missing: %s' % _config.privileged_key)

        try:
            _config.privileged_key = rsa.PublicKey.load_pkcs1(f.read())
        except Exception:
            raise exceptions.ConfigError(
                'Key at %s is not a valid RSA key' % _config.privileged_key)

    if _config.index_endpoint:
        _config.index_endpoint = _config.index_endpoint.strip('/')

    return _config
