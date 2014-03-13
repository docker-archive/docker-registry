import logging

import flask
import simplejson as json

import config
import mirroring
import signals
import storage
import toolkit

from .app import app


store = storage.load()
logger = logging.getLogger(__name__)

"""Those routes are loaded only when `standalone' is enabled in the config
   file. The goal is to make the Registry working without the central Index
   It's then possible to push images from Docker without talking to any other
   entities. This module mimics the Index.
"""


def get_endpoints(cfg=None):
    if not cfg:
        cfg = config.load()
    registry_endpoints = cfg.registry_endpoints
    if not registry_endpoints:
        #registry_endpoints = socket.gethostname()
        registry_endpoints = flask.request.environ['HTTP_HOST']
    return registry_endpoints


def generate_headers(namespace, repository, access):
    registry_endpoints = get_endpoints()
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
        json.loads(flask.request.data)
    except json.JSONDecodeError:
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
        data = json.loads(data) + json.loads(store.get_content(path))
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
        store.put_content(path, json.dumps(data))
        signals.repository_updated.send(
            sender, namespace=namespace, repository=repository, value=data)
    except IOError:
        signals.repository_created.send(
            sender, namespace=namespace, repository=repository,
            value=json.loads(data))
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
        data = json.loads(flask.request.data)
    except json.JSONDecodeError:
        return toolkit.api_error('Error Decoding JSON', 400)
    if not isinstance(data, list):
        return toolkit.api_error('Invalid data')
    update_index_images(namespace, repository, flask.request.data)
    headers = generate_headers(namespace, repository, 'write')
    code = 204 if images is True else 200
    return toolkit.response('', code, headers)


@app.route('/v1/repositories/<path:repository>/images', methods=['GET'])
@toolkit.parse_repository_name
@toolkit.requires_auth
@mirroring.source_lookup(index_route=True)
def get_repository_images(namespace, repository):
    data = None
    try:
        path = store.index_images_path(namespace, repository)
        data = store.get_content(path)
    except IOError:
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


@app.route('/v1/search', methods=['GET'])
def get_search():
    return toolkit.response({})
