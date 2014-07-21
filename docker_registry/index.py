# -*- coding: utf-8 -*-

import flask
import flask_cors

from docker_registry.core import compat
from docker_registry.core import exceptions
json = compat.json

from . import storage
from . import toolkit
from .lib import mirroring
from .lib import signals

from .app import app


store = storage.load()

"""Those routes are loaded only when `standalone' is enabled in the config
   file. The goal is to make the Registry working without the central Index
   It's then possible to push images from Docker without talking to any other
   entities. This module mimics the Index.
"""


def generate_headers(namespace, repository, access):
    registry_endpoints = toolkit.get_endpoints()
    # The token generated will be invalid against a real Index behind.
    token = 'Token signature={0},repository="{1}/{2}",access={3}'.format(
            toolkit.gen_random_string(), namespace, repository, access)
    return {'X-Docker-Endpoints': registry_endpoints,
            'WWW-Authenticate': token,
            'X-Docker-Token': token}


@app.route('/v1/users', methods=['GET', 'POST'])
@app.route('/v1/users/', methods=['GET', 'POST'])
def get_post_users():
    if flask.request.method == 'GET':
        return toolkit.response('OK', 200)
    try:
        # Note(dmp): unicode patch
        json.loads(flask.request.data.decode('utf8'))
    except ValueError:
        return toolkit.api_error('Error Decoding JSON', 400)
    return toolkit.response('User Created', 201)


@app.route('/v1/users/<username>/', methods=['PUT'])
def put_username(username):
    return toolkit.response('', 204)


def update_index_images(namespace, repository, data):
    path = store.index_images_path(namespace, repository)
    sender = flask.current_app._get_current_object()
    try:
        images = {}
        # Note(dmp): unicode patch
        data = json.loads(data.decode('utf8')) + store.get_json(path)
        for i in data:
            iid = i['id']
            if iid in images and 'checksum' in images[iid]:
                continue
            i_data = {'id': iid}
            for key in ['checksum']:
                if key in i:
                    i_data[key] = i[key]
            images[iid] = i_data
        data = images.values()
        # Note(dmp): unicode patch
        store.put_json(path, data)
        signals.repository_updated.send(
            sender, namespace=namespace, repository=repository, value=data)
    except exceptions.FileNotFoundError:
        signals.repository_created.send(
            sender, namespace=namespace, repository=repository,
            # Note(dmp): unicode patch
            value=json.loads(data.decode('utf8')))
        store.put_content(path, data)


@app.route('/v1/repositories/<path:repository>', methods=['PUT'])
@app.route('/v1/repositories/<path:repository>/images',
           defaults={'images': True},
           methods=['PUT'])
@toolkit.parse_repository_name
@toolkit.requires_auth
def put_repository(namespace, repository, images=False):
    data = None
    try:
        # Note(dmp): unicode patch
        data = json.loads(flask.request.data.decode('utf8'))
    except ValueError:
        return toolkit.api_error('Error Decoding JSON', 400)
    if not isinstance(data, list):
        return toolkit.api_error('Invalid data')
    update_index_images(namespace, repository, flask.request.data)
    headers = generate_headers(namespace, repository, 'write')
    code = 204 if images is True else 200
    return toolkit.response('', code, headers)


@app.route('/v1/repositories/<path:repository>/images', methods=['GET'])
@flask_cors.cross_origin(methods=['GET'])  # allow all origins (*)
@toolkit.parse_repository_name
@toolkit.requires_auth
@mirroring.source_lookup(index_route=True)
def get_repository_images(namespace, repository):
    data = None
    try:
        path = store.index_images_path(namespace, repository)
        data = store.get_content(path)
    except exceptions.FileNotFoundError:
        return toolkit.api_error('images not found', 404)
    headers = generate_headers(namespace, repository, 'read')
    return toolkit.response(data, 200, headers, True)


@app.route('/v1/repositories/<path:repository>/images', methods=['DELETE'])
@toolkit.parse_repository_name
@toolkit.requires_auth
def delete_repository_images(namespace, repository):
    # Does nothing, this file will be removed when DELETE on repos
    headers = generate_headers(namespace, repository, 'delete')
    return toolkit.response('', 204, headers)


@app.route('/v1/repositories/<path:repository>/auth', methods=['PUT'])
@toolkit.parse_repository_name
def put_repository_auth(namespace, repository):
    return toolkit.response('OK')
