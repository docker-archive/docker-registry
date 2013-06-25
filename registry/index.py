
import socket

import simplejson as json
from flask import request

import config
import storage
from toolkit import response, api_error, requires_auth, gen_random_string
from .app import app


store = storage.load()


""" Those routes are loaded only when `standalone' is enabled in the config
    file. The goal is to make the Registry working without the central Index
    It's then possible to push images from Docker without talking to any other
    entities. This module mimics the Index.
"""


def generate_headers(repository, access):
    cfg = config.load()
    registry_endpoints = cfg.registry_endpoints if cfg.registry_endpoints \
            else cfg.registry_endpoints
    # The token generated will be invalid against a real Index behind.
    token = 'Token signature={0},repository="{1}",access={2}'.format(
            gen_random_string(), repository, access)
    return {'X-Docker-Endpoints': registry_endpoints,
            'WWW-Authenticate': token,
            'X-Docker-Token': token}


@app.route('/v1/users/', methods=['GET', 'POST'])
def post_users():
    if request.method == 'GET':
        return response('OK', 200)
    data = None
    try:
        data = json.loads(request.data)
    except json.JSONDecodeError:
        return api_error('Error Decoding JSON', 400)
    return response('User Created', 201)


@app.route('/v1/users/<username>/', methods=['PUT'])
def put_user(username):
    return response('', 204)


@app.route('/v1/repositories/<namespace>/<repository>/', methods=['PUT'])
@requires_auth
def put_user_repo(namespace, repository):
    data = None
    try:
        data = json.loads(request.data)
    except json.JSONDecodeError:
        return api_error('Error Decoding JSON', 400)
    if not data or not isinstance(data, list):
        return api_error('Invalid data')
    store.put_content(store.repo_path(namespace, repository), request.data)
    headers = generate_headers('{0}/{1}'.format(namespace, repository),
            'write')
    return response('', 200, headers)


@app.route('/v1/repositories/<repository>/', methods=['PUT'])
@requires_auth
def put_library_repo(repository):
    data = None
    try:
        data = json.loads(request.data)
    except json.JSONDecodeError:
        return api_error('Error Decoding JSON', 400)
    if not data or not isinstance(data, list):
        return api_error('Invalid data')
    store.put_content(store.repo_path(repository), request.data)
    headers = generate_headers('library/{0}'.format(repository), 'write')
    return response('', 200, headers)


@app.route('/v1/repositories/<repository>/', methods=['DELETE'])
@requires_auth
def delete_library_repo(repository):
    try:
        store.remove(store.repo_path(repository))
    except oserror:
        return api_error('repo not found', 404)
    headers = generate_headers('library/{0}'.format(repository), 'delete')
    return response('', 200, headers)


@app.route('/v1/repositories/<namespace>/<repository>/images', methods=['PUT'])
@requires_auth
def put_user_images(namespace, repository):
    data = None
    try:
        data = json.loads(request.data)
    except json.JSONDecodeError:
        return api_error('Error Decoding JSON', 400)
    if not data or not isinstance(data, list):
        return api_error('Invalid data')
    store.put_content(store.repo_images_path(namespace, repository),
            request.data)
    headers = generate_headers('{0}/{1}'.format(namespace, repository),
            'write')
    return response('', 204, headers)


@app.route('/v1/repositories/<namespace>/<repository>/images', methods=['GET'])
@requires_auth
def get_user_images(namespace, repository):
    data = None
    try:
        data = store.get_content(store.repo_images_path(namespace, repository))
    except IOError:
        return api_error('images not found', 404)
    headers = generate_headers('{0}/{1}'.format(namespace, repository), 'read')
    return response(data, 200, headers, True)


@app.route('/v1/repositories/<namespace>/<repository>/images', methods=['DELETE'])
@requires_auth
def delete_user_images(namespace, repository):
    try:
        store.remove(store.repo_images_path(namespace, repository))
    except oserror:
        return api_error('images not found', 404)
    headers = generate_headers('{0}/{1}'.format(namespace, repository),
            'delete')
    return response('', 204, headers)


@app.route('/v1/repositories/<repository>/images', methods=['PUT'])
@requires_auth
def put_library_images(repository):
    data = None
    try:
        data = json.loads(request.data)
    except json.JSONDecodeError:
        return api_error('Error Decoding JSON', 400)
    if not data or not isinstance(data, list):
        return api_error('Invalid data')
    store.put_content(store.repo_images_path(repository), request.data)
    return response('', 204, generate_headers(repository, 'write'))


@app.route('/v1/repositories/<repository>/images', methods=['GET'])
@requires_auth
def get_library_images(repository):
    data = None
    try:
        data = store.get_content(store.repo_images_path(repository))
    except IOError:
        return api_error('images not found', 404)
    return response(data, 200, generate_headers(repository, 'read'), True)


@app.route('/v1/repositories/<repository>/images', methods=['DELETE'])
@requires_auth
def delete_library_images(repository):
    try:
        store.remove(store.repo_images_path(repository))
    except oserror:
        return api_error('images not found', 404)
    return response('', 204, generate_headers(repository, 'delete'))


@app.route('/v1/repositories/<namespace>/<repository>/auth', methods=['PUT'])
def put_user_repo_auth(namespace, repository):
    return response('OK')


@app.route('/v1/repositories/<repository>/auth', methods=['PUT'])
def put_library_repo_auth(repository):
    return response('OK')


@app.route('/v1/search', methods=['GET'])
def get_search():
    return response('{}')
