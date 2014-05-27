# -*- coding: utf-8 -*-

import flask
import functools
import logging
import requests

from .. import storage
from .. import toolkit
from . import cache
from . import config


DEFAULT_CACHE_TAGS_TTL = 48 * 3600
logger = logging.getLogger(__name__)


def is_mirror():
    cfg = config.load()
    return bool(cfg.get('mirroring', False))


def lookup_source(path, stream=False, source=None):
    if not source:
        cfg = config.load()
        mirroring_cfg = cfg.mirroring
        if not mirroring_cfg:
            return
        source = cfg.mirroring['source']
    source_url = '{0}{1}'.format(source, path)
    headers = {}
    for k, v in flask.request.headers.iteritems():
        if k.lower() != 'location' and k.lower() != 'host':
            headers[k] = v
    logger.debug('Request: GET {0}\nHeaders: {1}'.format(
        source_url, headers
    ))
    source_resp = requests.get(
        source_url,
        headers=headers,
        cookies=flask.request.cookies,
        stream=stream
    )
    if source_resp.status_code != 200:
        logger.debug('Source responded to request with non-200'
                     ' status')
        logger.debug('Response: {0}\n{1}\n'.format(
            source_resp.status_code, source_resp.text
        ))
        return None

    return source_resp


def source_lookup_tag(f):
    @functools.wraps(f)
    def wrapper(namespace, repository, *args, **kwargs):
        cfg = config.load()
        mirroring_cfg = cfg.mirroring
        resp = f(namespace, repository, *args, **kwargs)
        if not mirroring_cfg:
            return resp
        source = mirroring_cfg['source']
        tags_cache_ttl = mirroring_cfg.get('tags_cache_ttl',
                                           DEFAULT_CACHE_TAGS_TTL)

        if resp.status_code != 404:
            logger.debug('Status code is not 404, no source '
                         'lookup required')
            return resp

        if not cache.redis_conn:
            # No tags cache, just return
            logger.warning('mirroring: Tags cache is disabled, please set a '
                           'valid `cache\' directive in the config.')
            source_resp = lookup_source(
                flask.request.path, stream=False, source=source
            )
            if not source_resp:
                return resp

            headers = source_resp.headers
            if 'Content-Encoding' in headers:
                del headers['Content-Encoding']

            return toolkit.response(data=source_resp.content, headers=headers,
                                    raw=True)

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
            return toolkit.response(data=data, raw=True)
        source_resp = lookup_source(
            flask.request.path, stream=False, source=source
        )
        if not source_resp:
            return resp
        data = source_resp.content
        headers = source_resp.headers
        if 'Content-Encoding' in headers:
                del headers['Content-Encoding']

        cache.redis_conn.setex('{0}:{1}'.format(
            cache.cache_prefix, tag_path
        ), tags_cache_ttl, data)
        return toolkit.response(data=data, headers=headers,
                                raw=True)
    return wrapper


def source_lookup(cache=False, stream=False, index_route=False):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            cfg = config.load()
            mirroring_cfg = cfg.mirroring
            resp = f(*args, **kwargs)
            if not mirroring_cfg:
                return resp
            source = mirroring_cfg['source']
            if index_route:
                source = mirroring_cfg.get('source_index', source)
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

            headers = source_resp.headers
            if 'Content-Encoding' in headers:
                del headers['Content-Encoding']
            if index_route and 'X-Docker-Endpoints' in headers:
                headers['X-Docker-Endpoints'] = toolkit.get_endpoints()

            if not stream:
                logger.debug('JSON data found on source, writing response')
                resp_data = source_resp.content
                if cache:
                    store_mirrored_data(
                        resp_data, flask.request.url_rule.rule, kwargs,
                        store
                    )
                return toolkit.response(
                    data=resp_data,
                    headers=headers,
                    raw=True
                )
            logger.debug('Layer data found on source, preparing to '
                         'stream response...')
            layer_path = store.image_layer_path(kwargs['image_id'])
            return _handle_mirrored_layer(source_resp, layer_path, store,
                                          headers)

        return wrapper
    return decorator


def _handle_mirrored_layer(source_resp, layer_path, store, headers):
    sr = toolkit.SocketReader(source_resp)
    tmp, hndlr = storage.temp_store_handler()
    sr.add_handler(hndlr)

    def generate():
        for chunk in sr.iterate(store.buffer_size):
            yield chunk
        # FIXME: this could be done outside of the request context
        tmp.seek(0)
        store.stream_write(layer_path, tmp)
        tmp.close()
    return flask.Response(generate(), headers=headers)


def store_mirrored_data(data, endpoint, args, store):
    logger.debug('Endpoint: {0}'.format(endpoint))
    path_method, arglist = ({
        '/v1/images/<image_id>/json': ('image_json_path', ('image_id',)),
        '/v1/images/<image_id>/ancestry': (
            'image_ancestry_path', ('image_id',)
        ),
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
