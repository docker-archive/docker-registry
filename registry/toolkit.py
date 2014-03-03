import base64
import functools
import logging
import random
import re
import string
import urllib

import flask
import requests
import rsa
import simplejson as json

import cache
import config
import storage


logger = logging.getLogger(__name__)


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
                logger.debug('Read %d bytes' % len(chunk))
                for handler in self.handlers:
                    handler(chunk)
                yield chunk
        else:
            chunk = self._fp.read(chunk_size)
            while chunk:
                logger.debug('Read %d bytes' % len(chunk))
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
    return flask.current_app.make_response((data, code, h))


def check_session():
    session = flask.session
    if not session:
        logger.debug('check_session: Session is empty')
        return False
    if 'from' in session and get_remote_ip() != session['from']:
        logger.debug('check_session: Wrong source ip address')
        session.clear()
        return False
    # Session is valid
    return session.get('auth') is True


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
    headers = {'Authorization': flask.request.headers.get('authorization')}
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


_auth_exp = re.compile(r'(\w+)[:=][\s"]?([^",]+)"?')


def check_token(args):
    cfg = config.load()
    if cfg.disable_token_auth is True or cfg.standalone is not False:
        return True
    auth = flask.request.headers.get('authorization', '')
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
    # Token is valid, we create a session
    session = flask.session
    session['repository'] = auth.get('repository')
    session['auth'] = True
    if is_ssl() is False:
        # We enforce the IP check only when not using SSL
        session['from'] = get_remote_ip()
    return True


def is_mirror():
    cfg = config.load()
    return not not cfg.get('source')


def lookup_source(path, stream=False, source=None):
    if not source:
        cfg = config.load()
        source = cfg.get('source')
        if not source:
            return None
    source_url = '{0}{1}'.format(source, path)
    headers = {}
    for k, v in flask.request.headers.iteritems():
        if k.lower() != 'location' and k.lower() != 'host':
            headers[k] = v
    source_resp = requests.get(
        source_url,
        headers=headers,
        #cookies=flask.request.cookies,
        stream=stream
    )
    if source_resp.status_code != 200:
        logger.debug('Source responded to request with non-200'
                     ' status')
        logger.debug('Request: GET {0}\nHeaders: {1}'.format(
            source_url, headers
        ))
        logger.debug('Response: {0}\n{1}\n'.format(
            source_resp.status_code, source_resp.text
        ))
        return None

    return source_resp


def source_lookup_tag(f):
    @functools.wraps(f)
    def wrapper(namespace, repository, *args, **kwargs):
        cfg = config.load()
        source = cfg.get('source')
        tags_cache_cfg = cfg.get('tags_cache', None)
        cache_enabled = (tags_cache_cfg and
                         tags_cache_cfg.get('enabled', False) and
                         cache.redis_conn)
        ttl = tags_cache_cfg.get('ttl', 48 * 3600)
        resp = f(namespace, repository, *args, **kwargs)
        if not source:
            return resp

        if resp.status_code != 404:
            logger.debug('Status code is not 404, no source '
                         'lookup required')
            return resp

        if not cache_enabled:
            # No tags cache, just return
            source_resp = lookup_source(
                flask.request.path, stream=False, source=source
            )
            if not source_resp:
                return resp
            return response(data=source_resp.content,
                            headers=source_resp.headers, raw=True)

        store = storage.load()
        request_path = flask.request.path

        if request_path.endswith('/tags'):
            # client GETs a list of tags
            tag_path = store.tag_path(namespace, repository)
        else:
            # client GETs a single tag
            tag_path = store.tag_path(namespace, repository, kwargs['tag'])

        data = cache.redis_conn.get('{0}:{1}'.format(
            cache.cache_prefix, tag_path
        ))
        if data is not None:
            return response(data=data, headers=resp.headers, raw=True)
        source_resp = lookup_source(
            flask.request.path, stream=False, source=source
        )
        if not source_resp:
            return resp
        data = source_resp.content
        cache.redis_conn.setex('{0}:{1}'.format(
            cache.cache_prefix, tag_path
        ), ttl, data)
        return response(data=data, headers=source_resp.headers, raw=True)
    return wrapper


def source_lookup(cache=False, stream=False):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            cfg = config.load()
            source = cfg.get('source')
            resp = f(*args, **kwargs)
            if not source:
                return resp
            logger.debug('Source provided, registry acts as mirror')
            if resp.status_code != 404:
                logger.debug('Status code is not 404, no source '
                             'lookup required')
                return resp
            source_resp = lookup_source(
                flask.request.path, stream=stream, source=source
            )
            if not source_resp:
                return resp

            store = storage.load()

            if not stream:
                logger.debug('JSON data found on source, writing response')
                resp_data = source_resp.content
                if cache:
                    store_mirrored_data(
                        resp_data, flask.request.url_rule.rule, kwargs,
                        store
                    )
                return response(
                    data=resp_data,
                    headers=source_resp.headers,
                    raw=True
                )
            logger.debug('Layer data found on source, preparing to '
                         'stream response...')
            layer_path = store.image_layer_path(kwargs['image_id'])
            return _handle_mirrored_layer(source_resp, layer_path, store)

        return wrapper
    return decorator


def _handle_mirrored_layer(source_resp, layer_path, store):
    sr = SocketReader(source_resp)
    tmp, hndlr = storage.temp_store_handler()
    sr.add_handler(hndlr)

    def generate():
        for chunk in sr.iterate(store.buffer_size):
            yield chunk
        # FIXME: this could be done outside of the request context
        tmp.seek(0)
        store.stream_write(layer_path, tmp)
        tmp.close()
    return flask.Response(generate(), headers=source_resp.headers)


def store_mirrored_data(data, endpoint, args, store):
    logger.debug('Endpoint: {0}'.format(endpoint))
    path_method, arglist = ({
        '/v1/images/<image_id>/json': ('image_json_path', ('image_id',)),
        '/v1/images/<image_id>/ancestry': ('ancestry_path', ('image_id',)),
        '/v1/repositories/<path:repository>/json': (
            'registry_json_path', ('namespace', 'repository')
        ),
    }).get(endpoint, (None, None))
    if not path_method:
        return
    logger.debug('Path method: {0}'.format(path_method))
    pm_args = {}
    for arg in arglist:
        pm_args[arg] = args[arg]
    logger.debug('Path method args: {0}'.format(pm_args))
    storage_path = getattr(store, path_method)(**pm_args)
    logger.debug('Storage path: {0}'.format(storage_path))
    store.put_content(storage_path, data)


def check_signature():
    cfg = config.load()
    if not cfg.get('privileged_key'):
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
        return rsa.verify(message, sigdata, cfg.get('privileged_key'))
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
        if check_signature() is True or check_session() is True \
                or check_token(kwargs) is True:
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
    auth = dict(_auth_exp.findall(auth))
    repository = auth.get('repository')
    if repository is None:
        return ('', '')
    parts = repository.rstrip('/').split('/', 1)
    if len(parts) < 2:
        return ('library', parts[0])
    return (parts[0], parts[1])
