# -*- coding: utf-8 -*-

import functools
import string
import random
import time
import json
import re

from flask import current_app, request, session

import config


def response(data=None, code=200, headers=None):
    if data is None:
        data = True
    h = {
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'Expires': '-1',
        'Content-Type': 'application/json'
    }
    if headers:
        h.update(headers)
    try:
        data = json.dumps(data, indent=4, sort_keys=True, skipkeys=True)
        h['Content-Type'] = 'application/json'
    except TypeError:
        data = str(data)
    return current_app.make_response((data, code, h))


def check_session():
    def invalidate_session():
        session['timestamp'] = 0
        return False
    if not session:
        return False
    now = int(time.time())
    if (now - session.get('timestamp', 0)) > 3600:
        # Session expires after 1 hour
        return invalidate_session()
    if request.remote_addr != session.get('from'):
        return invalidate_session()
    # Session is valid, refresh it for one more hour
    session['timestamp'] = now
    return True


_auth_exp = re.compile(r'(\w+)[:=][\s"]?([^",]+)"?')
def check_token(args):
    cfg = config.load()
    if cfg.disable_token_auth is True:
        return True
    auth = request.headers.get('authorization', '')
    if auth.split(' ')[0].lower() != 'token':
        return False
    auth = dict(_auth_exp.findall(auth))
    if not auth:
        return False
    if 'namespace' in args and 'repository' in args:
        # We're authorizing an action on a repository,
        # let's check that it matches the repos name provided in the token
        full_repos_name = '{namespace}/{repository}'.format(**args)
        if full_repos_name != auth.get('repository'):
            return False
    # TODO(sam) implement token check on the Index
    # When implementing the token check, we'll get the checksums back
    # Fetch checksums and store it to Storage:/repositories/foo/bar/checksums
    # Then for every image push, we can fetch the file and see if it's in the checksum
    # Token is valid, we create a session
    session['from'] = request.remote_addr
    session['timestamp'] = int(time.time())
    session['repository'] = auth.get('repository')
    return True


def requires_auth(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if check_session() is True or check_token(kwargs) is True:
            return f(*args, **kwargs)
        headers = {'WWW-Authenticate': 'Token'}
        return api_error('Requires authorization', 401, headers)
    return wrapper


def api_error(message, code=400, headers=None):
    return response({'error': message}, code, headers)


def gen_random_string(length=16):
    return ''.join([random.choice(string.ascii_uppercase + string.digits)
        for x in range(length)])
