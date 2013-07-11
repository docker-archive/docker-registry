
import logging
import hashlib
import functools
import simplejson as json
from flask import request, Response, session

import storage
from toolkit import response, api_error, requires_auth
from .app import app


store = storage.load()
logger = logging.getLogger(__name__)


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


def compute_image_checksum(algo, image_id, json_data):
    algolib = getattr(hashlib, algo.lower())(json_data + '\n')
    for data in store.stream_read(store.image_layer_path(image_id)):
        algolib.update(data)
    return algolib.hexdigest()


def check_image_checksum(image_id, checksum, json_data):
    checksum_parts = checksum.split(':')
    computed_checksum = compute_image_checksum(checksum_parts[0],
                                               image_id,
                                               json_data)
    return computed_checksum == checksum_parts[1].lower()


@app.route('/v1/images/<image_id>/layer', methods=['PUT'])
@requires_auth
def put_image_layer(image_id):
    try:
        json_data = store.get_content(store.image_json_path(image_id))
    except IOError:
        return api_error('Image not found', 404)
    layer_path = store.image_layer_path(image_id)
    mark_path = store.image_mark_path(image_id)
    if store.exists(layer_path) and not store.exists(mark_path):
        return api_error('Image already exists', 409)
    input_stream = request.stream
    if request.headers.get('transfer-encoding') == 'chunked':
        # Careful, might work only with WSGI servers supporting chunked
        # encoding (Gunicorn)
        input_stream = request.environ['wsgi.input']
    store.stream_write(layer_path, input_stream)
    # FIXME(sam): Compute the checksum while uploading the image to save time
    try:
        checksum = store.get_content(store.image_checksum_path(image_id))
    except IOError:
        # We don't have a checksum stored yet, that's fine skipping the check.
        # Not removing the mark though, image is not downloadable yet.
        return response()
    if check_image_checksum(image_id, checksum, json_data) is False:
        logger.debug('put_image_layer: Wrong checksum')
        return api_error('Checksum mismatch, ignoring the layer')
    # Checksum is ok, we remove the marker
    store.remove(mark_path)
    return response()


@app.route('/v1/images/<image_id>/checksum', methods=['PUT'])
@requires_auth
def put_image_checksum(image_id):
    checksum = request.headers.get('x-docker-checksum', '')
    if not checksum:
        return api_error('Missing Image\'s checksum')
    try:
        json_data = store.get_content(store.image_json_path(image_id))
    except IOError:
        return api_error('Image not found', 404)
    mark_path = store.image_mark_path(image_id)
    if not store.exists(mark_path):
        return api_error('Cannot set this image checksum', 409)
    err = store_checksum(image_id, checksum)
    if err:
        return api_error(err)
    if check_image_checksum(image_id, checksum, json_data) is False:
        logger.debug('put_image_layer: Wrong checksum')
        return api_error('Checksum mismatch')
    # Checksum is ok, we remove the marker
    store.remove(mark_path)
    return response()


@app.route('/v1/images/<image_id>/json', methods=['GET'])
@requires_auth
@require_completion
def get_image_json(image_id):
    headers = {}
    try:
        data = store.get_content(store.image_json_path(image_id))
    except IOError:
        return api_error('Image not found', 404)
    try:
        size = store.get_size(store.image_layer_path(image_id))
        headers['X-Docker-Size'] = str(size)
    except OSError:
        pass
    checksum_path = store.image_checksum_path(image_id)
    if store.exists(checksum_path):
        headers['X-Docker-Checksum'] = store.get_content(checksum_path)
    return response(data, headers=headers, raw=True)


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
        path = store.images_list_path(*full_repos_name.split('/'))
        images_list = json.loads(store.get_content(path))
    except IOError:
        return False
    return (image_id in images_list)


def store_checksum(image_id, checksum):
    checksum_parts = checksum.split(':')
    if len(checksum_parts) != 2:
        return 'Invalid checksum format'
    if checksum_parts[0] not in hashlib.algorithms:
        return 'Checksum algorithm not supported'
    # We store the checksum
    checksum_path = store.image_checksum_path(image_id)
    store.put_content(checksum_path, checksum)


@app.route('/v1/images/<image_id>/json', methods=['PUT'])
@requires_auth
def put_image_json(image_id):
    try:
        data = json.loads(request.data)
    except json.JSONDecodeError:
        pass
    if not data or not isinstance(data, dict):
        return api_error('Invalid JSON')
    for key in ['id']:
        if key not in data:
            return api_error('Missing key `{0}\' in JSON'.format(key))
    # Read the checksum
    checksum = request.headers.get('x-docker-checksum', '')
    if checksum:
        # Storing the checksum is optional at this stage
        err = store_checksum(image_id, checksum)
        if err:
            return api_error(err)
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
        return api_error('Image already exists', 409)
    # If we reach that point, it means that this is a new image or a retry
    # on a failed push
    store.put_content(mark_path, 'true')
    store.put_content(json_path, request.data)
    generate_ancestry(image_id, parent_id)
    return response()
