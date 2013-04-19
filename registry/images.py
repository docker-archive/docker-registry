
import hashlib
import functools
import simplejson as json
from flask import request, Response, session

import storage
from toolkit import response, api_error, requires_auth
from .app import app


store = storage.load()


def require_completion(f):
    """ This make sure that the image push correctly finished """
    @functools.wraps(f)
    def wrapper(image_id):
        if store.exists(store.image_mark_path(image_id)):
            return api_error('Image is being uploaded, retry later')
        return f(image_id)
    return wrapper


@app.route('/v1/images/<image_id>/layer', methods=['GET'])
@requires_auth
@require_completion
def get_image_layer(image_id):
    try:
        return Response(store.stream_read(store.image_layer_path(
            image_id)))
    except IOError:
        return api_error('Image not found', 404)


def compute_image_checksum(image_id, algo):
    algolib = getattr(hashlib, algo.lower())()
    for data in store.stream_read(store.image_layer_path(image_id)):
        algolib.update(data)
    return algolib.hexdigest()


@app.route('/v1/images/<image_id>/layer', methods=['PUT'])
@requires_auth
def put_image_layer(image_id):
    try:
        info = json.loads(store.get_content(store.image_json_path(image_id)))
    except IOError:
        return api_error('JSON\'s image not found', 404)
    layer_path = store.image_layer_path(image_id)
    mark_path = store.image_mark_path(image_id)
    if store.exists(layer_path) and not store.exists(mark_path):
        return api_error('Image already exists')
    store.stream_write(layer_path, request.stream)
    # FIXME(sam): Compute the checksum while uploading the image to save time
    (algo, checksum) = info['checksum'].split(':')
    if compute_image_checksum(image_id, algo) != checksum.lower():
        return api_error('Checksum mismatch, ignoring the layer')
    # The checksum is ok, we remove the marker
    store.remove(mark_path)
    return response()


@app.route('/v1/images/<image_id>/json', methods=['GET'])
@requires_auth
@require_completion
def get_image_json(image_id):
    try:
        data = store.get_content(store.image_json_path(image_id))
    except IOError:
        return api_error('Image not found', 404)
    return response(json.loads(data))


@app.route('/v1/images/<image_id>/ancestry', methods=['GET'])
@requires_auth
@require_completion
def get_image_ancestry(image_id):
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


def check_images_list(image_id):
    full_repos_name = session.get('repository')
    if not full_repos_name:
        # We only enforce this check when there is a repos name in the session
        # otherwise it means that the auth is disabled.
        return True
    try:
        images_list = json.loads(store.get_content(path))
        path = self.images_list_path(*full_repos_name.split('/'))
    except IOError:
        return False
    return (image_id in images_list)


@app.route('/v1/images/<image_id>/json', methods=['PUT'])
@requires_auth
def put_image_json(image_id):
    try:
        data = json.loads(request.data)
    except json.JSONDecodeError:
        pass
    if not data or not isinstance(data, dict):
        return api_error('Invalid JSON')
    for key in ['id', 'checksum']:
        if key not in data:
            return api_error('Missing key `{0}\' in JSON'.format(key))
    checksum = data['checksum'].split(':')
    if len(checksum) != 2 or checksum[0].lower() not in hashlib.algorithms:
        return api_error('Invalid JSON format for `checksum\'')
    if image_id != data['id']:
        return api_error('JSON data contains invalid id')
    if check_images_list(image_id) is False:
        return api_error('This image does not belong to the repository')
    parent_id = data.get('parent')
    if parent_id and not store.exists(store.image_json_path(data['parent'])):
        return api_error('Image depends on a non existing parent')
    json_path = store.image_json_path(image_id)
    mark_path = store.image_mark_path(image_id)
    if store.exists(json_path) and not store.exists(mark_path):
        return api_error('Image already exists')
    # If we reach that point, it means that this is a new image or a retry
    # on a failed push
    store.put_content(mark_path, request.data)
    store.put_content(json_path, request.data)
    generate_ancestry(image_id, parent_id)
    return response()
