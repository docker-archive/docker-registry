
import os
import rsa
import yaml


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
    if isinstance(obj, dict):
        for i, value in obj.iteritems():
            obj[i] = _walk_object(value, callback)
        return obj
    for i, value in enumerate(obj):
        obj[i] = _walk_object(value, callback)
    return obj


def convert_env_vars(config):
    def _replace_env(s):
        if isinstance(s, basestring) and s.startswith('_env:'):
            parts = s.split(':', 2)
            varname = parts[1]
            vardefault = '!ENV_NOT_FOUND' if len(parts) < 3 else parts[2]
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
        config_path = os.path.join(os.path.dirname(__file__), '..',
                                   'config', config_path)
    with open(config_path) as f:
        data = yaml.load(f)
    config = data.get('common', {})
    flavor = os.environ.get('SETTINGS_FLAVOR', 'dev')
    config.update(data.get(flavor, {}))
    config['flavor'] = flavor
    config = convert_env_vars(config)
    if 'privileged_key' in config:
        with open(config['privileged_key']) as f:
            config['privileged_key'] = rsa.PublicKey.load_pkcs1(f.read())
    _config = Config(config)
    return _config
