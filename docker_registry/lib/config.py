# -*- coding: utf-8 -*-

import os
import rsa
import yaml

from docker_registry.core import exceptions


class Config(object):

    def __init__(self, config):
        self._config = config

    def __repr__(self):
        return repr(self._config)

    def __getattr__(self, key):
        if key in self._config:
            return self._config[key]

    def get(self, *args, **kwargs):
        return self._config.get(*args, **kwargs)


def _walk_object(obj, callback):
    if not hasattr(obj, '__iter__'):
        return callback(obj)
    obj_new = {}
    if isinstance(obj, dict):
        for i, value in obj.iteritems():
            value = _walk_object(value, callback)
            if value or value == '':
                obj_new[i] = value
        return obj_new
    for i, value in enumerate(obj):
        value = _walk_object(value, callback)
        if value or value == '':
            obj_new[i] = value
    return obj_new


def convert_env_vars(config):
    def _replace_env(s):
        if isinstance(s, basestring) and s.startswith('_env:'):
            parts = s.split(':', 2)
            varname = parts[1]
            vardefault = None if len(parts) < 3 else parts[2]
            return os.environ.get(varname, vardefault)
        return s

    return _walk_object(config, _replace_env)


_config = None


def load():
    global _config
    if _config is not None:
        return _config
    data = None
    config_path = os.environ.get('DOCKER_REGISTRY_CONFIG', 'config.yml')
    if not os.path.isabs(config_path):
        config_path = os.path.join(os.path.dirname(__file__), '../../',
                                   'config', config_path)
    try:
        f = open(config_path)
    except Exception:
        raise exceptions.FileNotFoundError(
            'Heads-up! File is missing: %s' % config_path)

    try:
        data = yaml.load(f)
    except Exception:
        raise exceptions.ConfigError(
            'Config file (%s) is not valid yaml' % config_path)

    config = data.get('common', {})
    flavor = os.environ.get('SETTINGS_FLAVOR', 'dev')
    config.update(data.get(flavor, {}))
    config['flavor'] = flavor
    config = convert_env_vars(config)
    if 'privileged_key' in config:
        try:
            f = open(config['privileged_key'])
        except Exception:
            raise exceptions.FileNotFoundError(
                'Heads-up! File is missing: %s' % config['privileged_key'])

        try:
            config['privileged_key'] = rsa.PublicKey.load_pkcs1(f.read())
        except Exception:
            raise exceptions.ConfigError(
                'Key at %s is not a valid RSA key' % config['privileged_key'])

    _config = Config(config)
    return _config
