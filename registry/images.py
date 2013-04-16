
import simplejson as json
from flask import request, Response

import storage
from toolkit import response, api_error
from .app import app


store = storage.load()


@app.route('/v1/images/<image_id>/layer', methods=['GET'])
def get_image_layer(image_id):
    try:
        return Response(store.stream_read(store.image_layer_path(
            image_id)))
    except IOError:
        return api_error('Image not found', 404)


@app.route('/v1/images/<image_id>/layer', methods=['PUT'])
def put_image_layer(image_id):
    if 'X-Docker-Checksum' not in request.headers:
        return api_error('X-Docker-Checksum not specified')
    if 'X-Docker-Algorithm' not in request.headers:
        return api_error('X-Docker-Algorithm not specified')
    if request.headers['X-Docker-Algorithm'] != 'sha256':
        return api_error('Algorithm not supported')
    if not store.exists(store.image_json_path(image_id)):
        return api_error('JSON\'s image not found', 404)
    store.stream_write(store.image_layer_path(image_id),
            request.stream)
    return response()


@app.route('/v1/images/<image_id>/json', methods=['GET'])
def get_image_json(image_id):
    data = None
    try:
        data = store.get_content(store.image_json_path(image_id))
    except IOError:
        return api_error('Image not found', 404)
    return response(json.loads(data))


@app.route('/v1/images/<image_id>/ancestry', methods=['GET'])
def get_image_ancestry(image_id):
    data = None
    try:
        data = store.get_content(store.image_ancestry_path(image_id))
    except IOError:
        return api_error('Image not found', 404)
    return response(json.loads(data))


def generate_ancestry(image_id, parent_id=None):
    if not parent_id:
        store.put_content(store.image_ancestry_path(image_id),
            json.dumps([image_id]))
        return
    data = store.get_content(store.image_ancestry_path(parent_id))
    data = json.loads(data)
    data.insert(0, image_id)
    store.put_content(store.image_ancestry_path(image_id), json.dumps(data))


@app.route('/v1/images/<image_id>/json', methods=['PUT'])
def put_image_json(image_id):
    data = None
    try:
        data = json.loads(request.data)
    except json.JSONDecodeError:
        pass
    if not data or 'id' not in data:
        return api_error('Invalid JSON')
    if image_id != data['id']:
        return api_error('JSON data contains invalid id')
    parent_id = data.get('parent')
    if parent_id and not store.exists(store.image_json_path(data['parent'])):
        return api_error('Image depends on a non existing parent')
    store.put_content(store.image_json_path(image_id), request.data)
    generate_ancestry(image_id, parent_id)
    return response()
