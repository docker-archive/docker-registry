import simplejson as json
import logging
from flask import request

import storage
from toolkit import response, api_error, requires_auth, parse_repository_name
from .app import app

store = storage.load()
logger = logging.getLogger(__name__)


@app.route('/v1/repositories/<path:repository>/tags',
           methods=['GET'])
@parse_repository_name
@requires_auth
def get_tags(namespace, repository):
    logger.debug("[get_tags] namespace={0}; repository={1}".format(namespace,
                 repository))
    data = {}
    try:
        for fname in store.list_directory(store.tag_path(namespace,
                                                         repository)):
            tag_name = fname.split('/').pop()
            if not tag_name.startswith('tag_'):
                continue
            data[tag_name[4:]] = store.get_content(fname)
    except OSError:
        return api_error('Repository not found', 404)
    return response(data)


@app.route('/v1/repositories/<path:repository>/tags/<tag>',
           methods=['GET'])
@parse_repository_name
@requires_auth
def get_tag(namespace, repository, tag):
    logger.debug("[get_tag] namespace={0}; repository={1}; tag={2}".format(
                 namespace, repository, tag))
    data = None
    try:
        data = store.get_content(store.tag_path(namespace, repository, tag))
    except IOError:
        return api_error('Tag not found', 404)
    return response(data)


@app.route('/v1/repositories/<path:repository>/tags/<tag>',
           methods=['PUT'])
@parse_repository_name
@requires_auth
def put_tag(namespace, repository, tag):
    logger.debug("[put_tag] namespace={0}; repository={1}; tag={2}".format(
                 namespace, repository, tag))
    data = None
    try:
        data = json.loads(request.data)
    except json.JSONDecodeError:
        pass
    if not data or not isinstance(data, basestring):
        return api_error('Invalid data')
    if not store.exists(store.image_json_path(data)):
        return api_error('Image not found', 404)
    store.put_content(store.tag_path(namespace, repository, tag), data)
    return response()


@app.route('/v1/repositories/<path:repository>/tags/<tag>',
           methods=['DELETE'])
@parse_repository_name
@requires_auth
def delete_tag(namespace, repository, tag):
    logger.debug("[delete_tag] namespace={0}; repository={1}; tag={2}".format(
                 namespace, repository, tag))
    try:
        store.remove(store.tag_path(namespace, repository, tag))
    except OSError:
        return api_error('Tag not found', 404)
    return response()


@app.route('/v1/repositories/<path:repository>/tags',
           methods=['DELETE'])
@parse_repository_name
@requires_auth
def delete_repository(namespace, repository):
    logger.debug("[delete_repository] namespace={0}; repository={1}".format(
                 namespace, repository))
    try:
        store.remove(store.tag_path(namespace, repository))
    except OSError:
        return api_error('Repository not found', 404)
    return response()
