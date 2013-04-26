
import functools
import logging
import string
import random
import time
import json
import re

from flask import current_app, request, session
import simplejson as json
import requests

import config
import storage

logger = logging.getLogger(__name__)


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


def validate_token(auth):
    full_repos_name = auth.get('repository', '').split('/')
    if len(full_repos_name) != 2:
        logger.debug('validate_token: Invalid repository field')
        return False
    cfg = config.load()
    index_endpoint = cfg.index_endpoint
    if index_endpoint is None:
        index_endpoint = 'https://api.docker.io'
    index_endpoint = index_endpoint.strip('/')
    url = '{0}/v1/repositories/{1}/{2}/images'.format(index_endpoint,
            full_repos_name[0], full_repos_name[1])
    headers = {'Authorization': request.headers.get('authorization')}
    resp = requests.get(url, verify=True, headers=headers)
    logger.debug('validate_token: Index returned {0}'.format(resp.status_code))
    if resp.status_code != 200:
        return False
    store = storage.load()
    try:
        images_list = [i['id'] for i in json.loads(resp.text)]
        store.put_content(store.images_list_path(*full_repos_name),
                json.dumps(images_list))
        logger.debug('validate_token: Wrong images_list')
    except json.JSONDecodeError:
        return False
    return True


_auth_exp = re.compile(r'(\w+)[:=][\s"]?([^",]+)"?')
def check_token(args):
    cfg = config.load()
    if cfg.disable_token_auth is True:
        return True
    auth = request.headers.get('authorization', '')
    if auth.split(' ')[0].lower() != 'token':
        logger.debug('check_token: Invalid token format')
        return False
    auth = dict(_auth_exp.findall(auth))
    if not auth:
        return False
    if 'namespace' in args and 'repository' in args:
        # We're authorizing an action on a repository,
        # let's check that it matches the repos name provided in the token
        full_repos_name = '{namespace}/{repository}'.format(**args)
        if full_repos_name != auth.get('repository'):
            logger.debug('check_token: Wrong repository name in the token')
            return False
    # Check that the token `access' variable is aligned with the HTTP method
    access = auth.get('access')
    if access == 'write' and request.method not in ['POST', 'PUT']:
        logger.debug('check_token: Wrong access value in the token')
        return False
    if access == 'read' and request.method != 'GET':
        logger.debug('check_token: Wrong access value in the token')
        return False
    if validate_token(auth) is False:
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
