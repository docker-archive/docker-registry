
import logging

import flask
import simplejson as json

import signals
import storage
import toolkit

from .app import app


store = storage.load()
logger = logging.getLogger(__name__)


@app.route('/v1/repositories/<path:repository>/properties', methods=['PUT'])
@toolkit.parse_repository_name
@toolkit.requires_auth
def set_properties(namespace, repo):
    logger.debug("[set_access] namespace={0}; repository={1}".format(namespace,
                 repo))
    data = None
    try:
        data = json.loads(flask.request.data)
    except json.JSONDecodeError:
        pass
    if not data or not isinstance(data, dict):
        return toolkit.api_error('Invalid data')
    private_flag_path = store.private_flag_path(namespace, repo)
    if data['access'] == 'private' and not store.is_private(namespace, repo):
        store.put_content(private_flag_path, '')
    elif data['access'] == 'public' and store.is_private(namespace, repo):
        store.remove(private_flag_path)
    return toolkit.response()


@app.route('/v1/repositories/<path:repository>/properties', methods=['GET'])
@toolkit.parse_repository_name
@toolkit.requires_auth
def get_properties(namespace, repo):
    logger.debug("[get_access] namespace={0}; repository={1}".format(namespace,
                 repo))
    is_private = store.is_private(namespace, repo)
    return toolkit.response({
        'access': 'private' if is_private else 'public'
    })


@app.route('/v1/repositories/<path:repository>/tags',
           methods=['GET'])
@toolkit.parse_repository_name
@toolkit.requires_auth
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
        return toolkit.api_error('Repository not found', 404)
    return toolkit.response(data)


@app.route('/v1/repositories/<path:repository>/tags/<tag>',
           methods=['GET'])
@toolkit.parse_repository_name
@toolkit.requires_auth
def get_tag(namespace, repository, tag):
    logger.debug("[get_tag] namespace={0}; repository={1}; tag={2}".format(
                 namespace, repository, tag))
    data = None
    try:
        data = store.get_content(store.tag_path(namespace, repository, tag))
    except IOError:
        return toolkit.api_error('Tag not found', 404)
    return toolkit.response(data)


@app.route('/v1/repositories/<path:repository>/tags/<tag>',
           methods=['PUT'])
@toolkit.parse_repository_name
@toolkit.requires_auth
def put_tag(namespace, repository, tag):
    logger.debug("[put_tag] namespace={0}; repository={1}; tag={2}".format(
                 namespace, repository, tag))
    data = None
    try:
        data = json.loads(flask.request.data)
    except json.JSONDecodeError:
        pass
    if not data or not isinstance(data, basestring):
        return toolkit.api_error('Invalid data')
    if not store.exists(store.image_json_path(data)):
        return toolkit.api_error('Image not found', 404)
    store.put_content(store.tag_path(namespace, repository, tag), data)
    sender = flask.current_app._get_current_object()
    signals.tag_created.send(sender, namespace=namespace,
                             repository=repository, tag=tag, value=data)
    return toolkit.response()


@app.route('/v1/repositories/<path:repository>/tags/<tag>',
           methods=['DELETE'])
@toolkit.parse_repository_name
@toolkit.requires_auth
def delete_tag(namespace, repository, tag):
    logger.debug("[delete_tag] namespace={0}; repository={1}; tag={2}".format(
                 namespace, repository, tag))
    try:
        store.remove(store.tag_path(namespace, repository, tag))
        sender = flask.current_app._get_current_object()
        signals.tag_deleted.send(sender, namespace=namespace,
                                 repository=repository, tag=tag)
    except OSError:
        return toolkit.api_error('Tag not found', 404)
    return toolkit.response()


@app.route('/v1/repositories/<path:repository>/tags',
           methods=['DELETE'])
@toolkit.parse_repository_name
@toolkit.requires_auth
def delete_repository(namespace, repository):
    logger.debug("[delete_repository] namespace={0}; repository={1}".format(
                 namespace, repository))
    try:
        store.remove(store.tag_path(namespace, repository))
        #TODO(samalba): Trigger tags_deleted signals
    except OSError:
        return toolkit.api_error('Repository not found', 404)
    return toolkit.response()
