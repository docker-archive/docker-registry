# -*- coding: utf-8 -*-

import datetime
import logging
import re
import time

import flask

from docker_registry.core import compat
from docker_registry.core import exceptions
json = compat.json

from . import storage
from . import toolkit
from .app import app
from .lib import mirroring
from .lib import signals


store = storage.load()
logger = logging.getLogger(__name__)
RE_USER_AGENT = re.compile('([^\s/]+)/([^\s/]+)')


@app.route('/v1/repositories/<path:repository>/properties', methods=['PUT'])
@toolkit.parse_repository_name
@toolkit.requires_auth
def set_properties(namespace, repository):
    logger.debug("[set_access] namespace={0}; repository={1}".format(namespace,
                 repository))
    data = None
    try:
        # Note(dmp): unicode patch
        data = json.loads(flask.request.data.decode('utf8'))
    except ValueError:
        pass
    if not data or not isinstance(data, dict):
        return toolkit.api_error('Invalid data')
    private_flag_path = store.private_flag_path(namespace, repository)
    if (data['access'] == 'private'
       and not store.is_private(namespace, repository)):
        store.put_content(private_flag_path, '')
    elif (data['access'] == 'public'
          and store.is_private(namespace, repository)):
        # XXX is this necessary? Or do we know for sure the file exists?
        try:
            store.remove(private_flag_path)
        except Exception:
            pass
    return toolkit.response()


@app.route('/v1/repositories/<path:repository>/properties', methods=['GET'])
@toolkit.parse_repository_name
@toolkit.requires_auth
def get_properties(namespace, repository):
    logger.debug("[get_access] namespace={0}; repository={1}".format(namespace,
                 repository))
    is_private = store.is_private(namespace, repository)
    return toolkit.response({
        'access': 'private' if is_private else 'public'
    })


def get_tags(namespace, repository):
    tag_path = store.tag_path(namespace, repository)
    for fname in store.list_directory(tag_path):
        full_tag_name = fname.split('/').pop()
        if not full_tag_name.startswith('tag_'):
            continue
        tag_name = full_tag_name[4:]
        tag_content = store.get_content(fname)
        yield (tag_name, tag_content)


@app.route('/v1/repositories/<path:repository>/tags', methods=['GET'])
@toolkit.parse_repository_name
@toolkit.requires_auth
@mirroring.source_lookup_tag
def _get_tags(namespace, repository):
    logger.debug("[get_tags] namespace={0}; repository={1}".format(namespace,
                 repository))
    try:
        data = dict((tag_name, tag_content)
                    for tag_name, tag_content
                    in get_tags(namespace=namespace, repository=repository))
    except exceptions.FileNotFoundError:
        return toolkit.api_error('Repository not found', 404)
    return toolkit.response(data)


@app.route('/v1/repositories/<path:repository>/tags/<tag>', methods=['GET'])
@toolkit.parse_repository_name
@toolkit.requires_auth
@mirroring.source_lookup_tag
def get_tag(namespace, repository, tag):
    logger.debug("[get_tag] namespace={0}; repository={1}; tag={2}".format(
                 namespace, repository, tag))
    data = None
    tag_path = store.tag_path(namespace, repository, tag)
    try:
        data = store.get_content(tag_path)
    except exceptions.FileNotFoundError:
        return toolkit.api_error('Tag not found', 404)
    return toolkit.response(data)


# warning: this endpoint is deprecated in favor of tag-specific json
# implemented by get_repository_tag_json
@app.route('/v1/repositories/<path:repository>/json', methods=['GET'])
@toolkit.parse_repository_name
@toolkit.requires_auth
@mirroring.source_lookup(stream=False, cache=True)
def get_repository_json(namespace, repository):
    json_path = store.repository_json_path(namespace, repository)
    headers = {}
    data = {'last_update': None,
            'docker_version': None,
            'docker_go_version': None,
            'arch': 'amd64',
            'os': 'linux',
            'kernel': None}
    try:
        # Note(dmp): unicode patch
        data = store.get_json(json_path)
    except exceptions.FileNotFoundError:
        if mirroring.is_mirror():
            # use code 404 to trigger the source_lookup decorator.
            # TODO(joffrey): make sure this doesn't break anything or have the
            # decorator rewrite the status code before sending
            return toolkit.response(data, code=404, headers=headers)
        # else we ignore the error, we'll serve the default json declared above
    return toolkit.response(data, headers=headers)


@app.route(
    '/v1/repositories/<path:repository>/tags/<tag>/json',
    methods=['GET'])
@toolkit.parse_repository_name
@toolkit.requires_auth
def get_repository_tag_json(namespace, repository, tag):
    json_path = store.repository_tag_json_path(namespace, repository, tag)
    data = {'last_update': None,
            'docker_version': None,
            'docker_go_version': None,
            'arch': 'amd64',
            'os': 'linux',
            'kernel': None}
    try:
        # Note(dmp): unicode patch
        data = store.get_json(json_path)
    except exceptions.FileNotFoundError:
        # We ignore the error, we'll serve the default json declared above
        pass
    return toolkit.response(data)


def create_tag_json(user_agent):
    props = {
        'last_update': int(time.mktime(datetime.datetime.utcnow().timetuple()))
    }
    ua = dict(RE_USER_AGENT.findall(user_agent))
    if 'docker' in ua:
        props['docker_version'] = ua['docker']
    if 'go' in ua:
        props['docker_go_version'] = ua['go']
    for k in ['arch', 'kernel', 'os']:
        if k in ua:
            props[k] = ua[k].lower()
    return json.dumps(props)


@app.route('/v1/repositories/<path:repository>/tags/<tag>',
           methods=['PUT'])
@toolkit.parse_repository_name
@toolkit.requires_auth
def put_tag(namespace, repository, tag):
    logger.debug("[put_tag] namespace={0}; repository={1}; tag={2}".format(
                 namespace, repository, tag))
    data = None
    try:
        # Note(dmp): unicode patch
        data = json.loads(flask.request.data.decode('utf8'))
    except ValueError:
        pass
    if not data or not isinstance(data, basestring):
        return toolkit.api_error('Invalid data')
    if not store.exists(store.image_json_path(data)):
        return toolkit.api_error('Image not found', 404)
    store.put_content(store.tag_path(namespace, repository, tag), data)
    sender = flask.current_app._get_current_object()
    signals.tag_created.send(sender, namespace=namespace,
                             repository=repository, tag=tag, value=data)
    # Write some meta-data about the repos
    ua = flask.request.headers.get('user-agent', '')
    data = create_tag_json(user_agent=ua)
    json_path = store.repository_tag_json_path(namespace, repository, tag)
    store.put_content(json_path, data)
    if tag == "latest":  # TODO(dustinlacewell) : deprecate this for v2
        json_path = store.repository_json_path(namespace, repository)
        store.put_content(json_path, data)
    return toolkit.response()


def delete_tag(namespace, repository, tag):
    logger.debug("[delete_tag] namespace={0}; repository={1}; tag={2}".format(
                 namespace, repository, tag))
    store.remove(store.tag_path(namespace, repository, tag))
    store.remove(store.repository_tag_json_path(namespace, repository,
                                                tag))
    sender = flask.current_app._get_current_object()
    if tag == "latest":  # TODO(wking) : deprecate this for v2
        store.remove(store.repository_json_path(namespace, repository))
    signals.tag_deleted.send(
        sender, namespace=namespace, repository=repository, tag=tag)


@app.route('/v1/repositories/<path:repository>/tags/<tag>',
           methods=['DELETE'])
@toolkit.parse_repository_name
@toolkit.requires_auth
def _delete_tag(namespace, repository, tag):
    # XXX backends are inconsistent on this - some will throw, but not all
    try:
        delete_tag(namespace=namespace, repository=repository, tag=tag)
    except exceptions.FileNotFoundError:
        return toolkit.api_error('Tag not found', 404)
    return toolkit.response()


@app.route('/v1/repositories/<path:repository>/', methods=['DELETE'])
@app.route('/v1/repositories/<path:repository>/tags', methods=['DELETE'])
@toolkit.parse_repository_name
@toolkit.requires_auth
def delete_repository(namespace, repository):
    """Remove a repository from storage

    This endpoint exists in both the registry API [1] and the indexer
    API [2], but has the same semantics in each instance.  It's in the
    tags module (instead of the index module which handles most
    repository tasks) because it should be available regardless of
    whether the rest of the index-module endpoints are enabled via the
    'standalone' config setting.

    [1]: http://docs.docker.io/en/latest/reference/api/registry_api/#delete--v1-repositories-%28namespace%29-%28repository%29- # nopep8
    [2]: http://docs.docker.io/en/latest/reference/api/index_api/#delete--v1-repositories-%28namespace%29-%28repo_name%29- # nopep8
    """
    logger.debug("[delete_repository] namespace={0}; repository={1}".format(
                 namespace, repository))
    try:
        for tag_name, tag_content in get_tags(
                namespace=namespace, repository=repository):
            delete_tag(
                namespace=namespace, repository=repository, tag=tag_name)
        # TODO(wking): remove images, but may need refcounting
        store.remove(store.repository_path(
            namespace=namespace, repository=repository))
    except exceptions.FileNotFoundError:
        return toolkit.api_error('Repository not found', 404)
    else:
        sender = flask.current_app._get_current_object()
        signals.repository_deleted.send(
            sender, namespace=namespace, repository=repository)
    return toolkit.response()
