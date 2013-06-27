
import functools
import logging
import string
import random
import urllib
import time
import re

from flask import current_app, request, session
import simplejson as json
import requests

import config
import storage


logger = logging.getLogger(__name__)


def response(data=None, code=200, headers=None, raw=False):
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
        if raw is False:
            data = json.dumps(data, indent=4, sort_keys=True, skipkeys=True)
    except TypeError:
        data = str(data)
    return current_app.make_response((data, code, h))


def check_session():
    def invalidate_session():
        session['timestamp'] = 0
        return False
    if not session:
        logger.debug('check_session: Session is empty')
        return False
    now = int(time.time())
    if (now - session.get('timestamp', 0)) > 3600:
        # Session expires after 1 hour
        logger.debug('check_session: Session expired')
        return invalidate_session()
    if get_remote_ip() != session.get('from'):
        logger.debug('check_session: Wrong source ip address')
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
        index_endpoint = 'https://index.docker.io'
    index_endpoint = index_endpoint.strip('/')
    url = '{0}/v1/repositories/{1}/{2}/images'.format(index_endpoint,
                                                      full_repos_name[0],
                                                      full_repos_name[1])
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
    except json.JSONDecodeError:
        logger.debug('validate_token: Wrong format for images_list')
        return False
    return True


def get_remote_ip():
    if 'x-real-ip' in request.headers:
        return request.headers['x-real-ip']
    return request.remote_addr


_auth_exp = re.compile(r'(\w+)[:=][\s"]?([^",]+)"?')


def check_token(args):
    cfg = config.load()
    if cfg.disable_token_auth is True or cfg.standalone is True:
        return True
    auth = request.headers.get('authorization', '')
    if auth.split(' ')[0].lower() != 'token':
        logger.debug('check_token: Invalid token format')
        return False
    logger.debug('args = {0}'.format(args))
    logger.debug('Auth Token = {0}'.format(auth))
    auth = dict(_auth_exp.findall(auth))
    logger.debug('auth = {0}'.format(auth))
    if not auth:
        return False
    if 'namespace' in args and 'repository' in args:
        # We're authorizing an action on a repository,
        # let's check that it matches the repos name provided in the token
        full_repos_name = '{namespace}/{repository}'.format(**args)
        logger.debug('full_repos_name  = {0}'.format(full_repos_name))
        if full_repos_name != auth.get('repository'):
            logger.debug('check_token: Wrong repository name in the token:'
                         '{0} != {1}'.format(full_repos_name,
                                             auth.get('repository')))
            return False
    # Check that the token `access' variable is aligned with the HTTP method
    access = auth.get('access')
    if access == 'write' and request.method not in ['POST', 'PUT']:
        logger.debug('check_token: Wrong access value in the token')
        return False
    if access == 'read' and request.method != 'GET':
        logger.debug('check_token: Wrong access value in the token')
        return False
    if access == 'delete' and request.method != 'DELETE':
        logger.debug('check_token: Wrong access value in the token')
        return False
    if validate_token(auth) is False:
        return False
    # Token is valid, we create a session
    session['from'] = get_remote_ip()
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
    logger.debug('api_error: {0}'.format(message))
    return response({'error': message}, code, headers)


def gen_random_string(length=16):
    return ''.join([random.choice(string.ascii_uppercase + string.digits)
                    for x in range(length)])


def encode_repository_name(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if 'repository' in kwargs:
            kwargs['repository'] = urllib.quote_plus(kwargs['repository'])
        return f(*args, **kwargs)
    return wrapper
