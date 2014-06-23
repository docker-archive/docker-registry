# -*- coding: utf-8 -*-

import base64
import distutils.version
import functools
import logging
import random
import re
import string
import urllib

import flask
import requests
import rsa

from docker_registry.core import compat
json = compat.json

from . import storage
from .lib import config

cfg = config.load()
logger = logging.getLogger(__name__)
_re_docker_version = re.compile('docker/([^\s]+)')
_re_authorization = re.compile(r'(\w+)[:=][\s"]?([^",]+)"?')


class DockerVersion(distutils.version.StrictVersion):

    def __init__(self):
        ua = flask.request.headers.get('user-agent', '')
        m = _re_docker_version.search(ua)
        if not m:
            raise RuntimeError('toolkit.DockerVersion: cannot parse version')
        version = m.group(1)
        if '-' in version:
            version = version.split('-')[0]
        distutils.version.StrictVersion.__init__(self, version)


class SocketReader(object):

    def __init__(self, fp):
        self._fp = fp
        self.handlers = []

    def __iter__(self):
        return self.iterate()

    def iterate(self, chunk_size=-1):
        if isinstance(self._fp, requests.Response):
            if chunk_size == -1:
                chunk_size = 1024
            for chunk in self._fp.iter_content(chunk_size):
                for handler in self.handlers:
                    handler(chunk)
                yield chunk
        else:
            chunk = self._fp.read(chunk_size)
            while chunk:
                for handler in self.handlers:
                    handler(chunk)
                yield chunk
                chunk = self._fp.read(chunk_size)

    def add_handler(self, handler):
        self.handlers.append(handler)

    def read(self, n=-1):
        buf = self._fp.read(n)
        if not buf:
            return ''
        for handler in self.handlers:
            handler(buf)
        return buf


def response(data=None, code=200, headers=None, raw=False):
    if data is None:
        data = True
    h = {
        'Cache-Control': 'no-cache',
        'Expires': '-1',
        'Content-Type': 'application/json'
    }
    if headers:
        h.update(headers)

    if h['Cache-Control'] == 'no-cache':
        h['Pragma'] = 'no-cache'

    try:
        if raw is False:
            data = json.dumps(data, sort_keys=True, skipkeys=True)
    except TypeError:
        data = str(data)
    return flask.current_app.make_response((data, code, h))


def validate_parent_access(parent_id):
    if cfg.standalone:
        return True
    auth = _parse_auth_header()
    if not auth:
        return False
    full_repos_name = auth.get('repository', '').split('/')
    if len(full_repos_name) != 2:
        logger.debug('validate_parent: Invalid repository field')
        return False
    url = '{0}/v1/repositories/{1}/{2}/layer/{3}/access'.format(
        cfg.index_endpoint, full_repos_name[0], full_repos_name[1], parent_id
    )
    headers = {'Authorization': flask.request.headers.get('authorization')}
    resp = requests.get(url, verify=True, headers=headers)
    if resp.status_code != 200:
        logger.debug('validate_parent: index returns status {0}'.format(
            resp.status_code
        ))
        return False
    try:
        # Note(dmp): unicode patch XXX not applied! Assuming requests does it
        logger.debug('validate_parent: Content: {0}'.format(resp.text))
        return json.loads(resp.text).get('access', False)
    except ValueError:
        logger.debug('validate_parent: Wrong response format')
        return False


def validate_token(auth):
    full_repos_name = auth.get('repository', '').split('/')
    if len(full_repos_name) != 2:
        logger.debug('validate_token: Invalid repository field')
        return False
    url = '{0}/v1/repositories/{1}/{2}/images'.format(cfg.index_endpoint,
                                                      full_repos_name[0],
                                                      full_repos_name[1])
    headers = {'Authorization': flask.request.headers.get('authorization')}
    resp = requests.get(url, verify=True, headers=headers)
    logger.debug('validate_token: Index returned {0}'.format(resp.status_code))
    if resp.status_code != 200:
        return False
    store = storage.load()
    try:
        # Note(dmp): unicode patch XXX not applied (requests)
        images_list = [i['id'] for i in json.loads(resp.text)]
        store.put_content(store.images_list_path(*full_repos_name),
                          json.dumps(images_list))
    except ValueError:
        logger.debug('validate_token: Wrong format for images_list')
        return False
    return True


def get_remote_ip():
    if 'X-Forwarded-For' in flask.request.headers:
        return flask.request.headers.getlist('X-Forwarded-For')[0]
    if 'X-Real-Ip' in flask.request.headers:
        return flask.request.headers.getlist('X-Real-Ip')[0]
    return flask.request.remote_addr


def is_ssl():
    for header in ('X-Forwarded-Proto', 'X-Forwarded-Protocol'):
        if header in flask.request.headers and \
                flask.request.headers[header].lower() in ('https', 'ssl'):
                    return True
    return False


def _parse_auth_header():
    auth = flask.request.headers.get('authorization', '')
    if auth.split(' ')[0].lower() != 'token':
        logger.debug('check_token: Invalid token format')
        return None
    logger.debug('Auth Token = {0}'.format(auth))
    auth = dict(_re_authorization.findall(auth))
    logger.debug('auth = {0}'.format(auth))
    return auth


def check_token(args):
    logger.debug('args = {0}'.format(args))
    if cfg.disable_token_auth is True or cfg.standalone is True:
        return True
    auth = _parse_auth_header()
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
    if access == 'write' and flask.request.method not in ['POST', 'PUT']:
        logger.debug('check_token: Wrong access value in the token')
        return False
    if access == 'read' and flask.request.method != 'GET':
        logger.debug('check_token: Wrong access value in the token')
        return False
    if access == 'delete' and flask.request.method != 'DELETE':
        logger.debug('check_token: Wrong access value in the token')
        return False
    if validate_token(auth) is False:
        return False
    # Token is valid
    return True


def check_signature():
    if not cfg.privileged_key:
        return False
    headers = flask.request.headers
    signature = headers.get('X-Signature')
    if not signature:
        logger.debug('No X-Signature header in request')
        return False
    sig = parse_content_signature(signature)
    logger.debug('Parsed signature: {}'.format(sig))
    sigdata = base64.b64decode(sig['data'])
    header_keys = sorted([
        x for x in headers.iterkeys() if x.startswith('X-Docker')
    ])
    message = ','.join([flask.request.method, flask.request.path] +
                       ['{}:{}'.format(k, headers[k]) for k in header_keys])
    logger.debug('Signed message: {}'.format(message))
    try:
        return rsa.verify(message, sigdata, cfg.privileged_key)
    except rsa.VerificationError:
        return False


def parse_content_signature(s):
    lst = [x.strip().split('=', 1) for x in s.split(';')]
    ret = {}
    for k, v in lst:
        ret[k] = v
    return ret


def requires_auth(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if check_signature() is True or check_token(kwargs) is True:
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


def parse_repository_name(f):
    @functools.wraps(f)
    def wrapper(repository, *args, **kwargs):
        parts = repository.rstrip('/').split('/', 1)
        if len(parts) < 2:
            namespace = 'library'
            repository = parts[0]
        else:
            (namespace, repository) = parts
        repository = urllib.quote_plus(repository)
        return f(namespace, repository, *args, **kwargs)
    return wrapper


def get_repository():
    auth = flask.request.headers.get('authorization', '')
    if not auth:
        return
    auth = dict(_re_authorization.findall(auth))
    repository = auth.get('repository')
    if repository is None:
        return ('', '')
    parts = repository.rstrip('/').split('/', 1)
    if len(parts) < 2:
        return ('library', parts[0])
    return (parts[0], parts[1])


def get_endpoints(overcfg=None):
    registry_endpoints = (overcfg or cfg).registry_endpoints
    if not registry_endpoints:
        #registry_endpoints = socket.gethostname()
        registry_endpoints = flask.request.environ['HTTP_HOST']
    return registry_endpoints
