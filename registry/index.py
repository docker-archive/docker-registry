
import simplejson as json
from flask import request

import config
import storage
from toolkit import response, api_error, requires_auth, gen_random_string, \
    parse_repository_name
from .app import app


store = storage.load()


""" Those routes are loaded only when `standalone' is enabled in the config
    file. The goal is to make the Registry working without the central Index
    It's then possible to push images from Docker without talking to any other
    entities. This module mimics the Index.
"""


def generate_headers(namespace, repository, access):
    cfg = config.load()
    registry_endpoints = cfg.registry_endpoints
    if not registry_endpoints:
        #registry_endpoints = socket.gethostname()
        registry_endpoints = request.environ['HTTP_HOST']
    # The token generated will be invalid against a real Index behind.
    token = 'Token signature={0},repository="{1}/{2}",access={3}'.format(
            gen_random_string(), namespace, repository, access)
    return {'X-Docker-Endpoints': registry_endpoints,
            'WWW-Authenticate': token,
            'X-Docker-Token': token}


@app.route('/v1/users', methods=['GET', 'POST'])
@app.route('/v1/users/', methods=['GET', 'POST'])
def get_post_users():
    if request.method == 'GET':
        return response('OK', 200)
    try:
        json.loads(request.data)
    except json.JSONDecodeError:
        return api_error('Error Decoding JSON', 400)
    return response('User Created', 201)


@app.route('/v1/users/<username>/', methods=['PUT'])
def put_username(username):
    return response('', 204)


def update_index_images(namespace, repository, data):
    path = store.index_images_path(namespace, repository)
    try:
        images = {}
        data = json.loads(data) + store.get_content(data)
        for i in data:
            iid = i['id']
            if iid in images and 'checksum' in images[iid]:
                continue
            images[iid] = i
        data = images.values()
        store.put_content(path, json.dumps(data.values()))
    except IOError:
        store.put_content(path, data)


@app.route('/v1/repositories/<path:repository>', methods=['PUT'])
@app.route('/v1/repositories/<path:repository>/images', methods=['PUT'])
@parse_repository_name
@requires_auth
def put_repository(namespace, repository):
    data = None
    try:
        data = json.loads(request.data)
    except json.JSONDecodeError:
        return api_error('Error Decoding JSON', 400)
    if not data or not isinstance(data, list):
        return api_error('Invalid data')
    update_index_images(namespace, repository, request.data)
    headers = generate_headers(namespace, repository, 'write')
    return response('', 200, headers)


@app.route('/v1/repositories/<path:repository>/images', methods=['GET'])
@parse_repository_name
@requires_auth
def get_repository_images(namespace, repository):
    data = None
    try:
        path = store.index_images_path(namespace, repository)
        data = store.get_content(path)
    except IOError:
        return api_error('images not found', 404)
    headers = generate_headers(namespace, repository, 'read')
    return response(data, 200, headers, True)


@app.route('/v1/repositories/<path:repository>/images', methods=['DELETE'])
@parse_repository_name
@requires_auth
def delete_repository_images(namespace, repository):
    # Does nothing, this file will be removed when DELETE on repos
    headers = generate_headers(namespace, repository, 'delete')
    return response('', 204, headers)


@app.route('/v1/repositories/<path:repository>/auth', methods=['PUT'])
@parse_repository_name
def put_repository_auth(namespace, repository):
    return response('OK')


@app.route('/v1/search', methods=['GET'])
def get_search():
    return response('{}')
