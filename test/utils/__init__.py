
'''General use testing library'''


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
