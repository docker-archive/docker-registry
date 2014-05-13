# -*- coding: utf-8 -*-


def monkeypatch_method(cls):
    '''Guido's monkeypatch decorator.'''
    def decorator(func):
        setattr(cls, func.__name__, func)
        return func
    return decorator


def monkeypatch_class(name, bases, namespace):
    '''Guido's monkeypatch metaclass.'''
    assert len(bases) == 1, "Exactly one base class required"
    base = bases[0]
    for name, value in namespace.iteritems():
        if name != "__metaclass__":
            setattr(base, name, value)
    return base


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
