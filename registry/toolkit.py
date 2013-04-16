# -*- coding: utf-8 -*-

import functools
import json

from flask import current_app, request

from exceptions import JSONBadRequest


def response(data=None, code=200, headers=None):
    if data is None:
        data = 'ok'
    h = {
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'Expires': '-1',
        'Content-Type': 'application/json'
    }
    if headers:
        h.update(headers)
    if not isinstance(data, basestring):
        try:
            data = json.dumps(
                data, indent=4, sort_keys=True, skipkeys=True
            )
            h['Content-Type'] = 'application/json'
        except TypeError:
            data = str(data)
    return current_app.make_response((data, code, h))


def jsonrequest(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if request.json is None:
            raise JSONBadRequest(
                "Expected application/json but got {0} instead".format(
                    request.mimetype
                )
            )
        return f(*args, **kwargs)
    return wrapper


def requires_auth(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        #TODO: Implement token checks
        return f(*args, **kwargs)
    return decorated


def api_error(message, code=400, headers=None):
    return response({'error': message}, code, headers)
