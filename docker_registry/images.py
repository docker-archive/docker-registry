# -*- coding: utf-8 -*-

import datetime
import functools
import logging
import time

import flask

from docker_registry.core import compat
from docker_registry.core import exceptions
json = compat.json

from . import storage
from . import toolkit
from .app import app
from .app import cfg
from .lib import cache
from .lib import checksums
from .lib import layers
from .lib import mirroring
# this is our monkey patched snippet from python v2.7.6 'tarfile'
# with xattr support
from .lib.xtarfile import tarfile


store = storage.load()
logger = logging.getLogger(__name__)


def require_completion(f):
    """This make sure that the image push correctly finished."""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if store.exists(store.image_mark_path(kwargs['image_id'])):
            return toolkit.api_error('Image is being uploaded, retry later')
        return f(*args, **kwargs)
    return wrapper


def set_cache_headers(f):
    """Returns HTTP headers suitable for caching."""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        # Set TTL to 1 year by default
        ttl = 31536000
        expires = datetime.datetime.fromtimestamp(int(time.time()) + ttl)
        expires = expires.strftime('%a, %d %b %Y %H:%M:%S GMT')
        headers = {
            'Cache-Control': 'public, max-age={0}'.format(ttl),
            'Expires': expires,
            'Last-Modified': 'Thu, 01 Jan 1970 00:00:00 GMT',
        }
        if 'If-Modified-Since' in flask.request.headers:
            return flask.Response(status=304, headers=headers)
        kwargs['headers'] = headers
        # Prevent the Cookie to be sent when the object is cacheable
        return f(*args, **kwargs)
    return wrapper


def _get_image_layer(image_id, headers=None, bytes_range=None):
    if headers is None:
        headers = {}

    headers['Content-Type'] = 'application/octet-stream'
    accel_uri_prefix = cfg.nginx_x_accel_redirect
    path = store.image_layer_path(image_id)
    if accel_uri_prefix:
        if store.scheme == 'file':
            accel_uri = '/'.join([accel_uri_prefix, path])
            headers['X-Accel-Redirect'] = accel_uri
            logger.debug('send accelerated {0} ({1})'.format(
                accel_uri, headers))
            return flask.Response('', headers=headers)
        else:
            logger.warn('nginx_x_accel_redirect config set,'
                        ' but storage is not LocalStorage')

    # If store allows us to just redirect the client let's do that, we'll
    # offload a lot of expensive I/O and get faster I/O
    if cfg.storage_redirect:
        try:
            content_redirect_url = store.content_redirect_url(path)
            if content_redirect_url:
                return flask.redirect(content_redirect_url, 302)
        except IOError as e:
            logger.debug(str(e))

    status = None
    layer_size = 0

    if not store.exists(path):
        raise exceptions.FileNotFoundError("Image layer absent from store")
    try:
        layer_size = store.get_size(path)
    except exceptions.FileNotFoundError:
        # XXX why would that fail given we know the layer exists?
        pass
    if bytes_range and bytes_range[1] == -1 and not layer_size == 0:
        bytes_range = (bytes_range[0], layer_size)

    if bytes_range:
        content_length = bytes_range[1] - bytes_range[0] + 1
        if not _valid_bytes_range(bytes_range):
            return flask.Response(status=416, headers=headers)
        status = 206
        content_range = (bytes_range[0], bytes_range[1], layer_size)
        headers['Content-Range'] = '{0}-{1}/{2}'.format(*content_range)
        headers['Content-Length'] = content_length
    elif layer_size > 0:
        headers['Content-Length'] = layer_size
    else:
        return flask.Response(status=416, headers=headers)
    return flask.Response(store.stream_read(path, bytes_range),
                          headers=headers, status=status)


def _get_image_json(image_id, headers=None):
    if headers is None:
        headers = {}
    data = store.get_content(store.image_json_path(image_id))
    try:
        size = store.get_size(store.image_layer_path(image_id))
        headers['X-Docker-Size'] = str(size)
    except exceptions.FileNotFoundError:
        pass
    try:
        csums = load_checksums(image_id)
        headers['X-Docker-Payload-Checksum'] = csums
    except exceptions.FileNotFoundError:
        pass
    return toolkit.response(data, headers=headers, raw=True)


def _parse_bytes_range():
    headers = flask.request.headers
    range_header = headers.get('range')
    if not range_header:
        return
    log_msg = ('_parse_bytes_range: Malformed bytes range request header: '
               '{0}'.format(range_header))
    if not range_header.startswith('bytes='):
        logger.debug(log_msg)
        return
    bytes_range = range_header[6:].split('-')
    if len(bytes_range) != 2 and not range_header[-1] == '-':
        logger.debug(log_msg)
        return
    if len(bytes_range) == 1 or bytes_range[1] == '':
        bytes_range = (bytes_range[0], -1)
        try:
            return (int(bytes_range[0]), -1)
        except ValueError:
            logger.debug(log_msg)
    try:
        return (int(bytes_range[0]), int(bytes_range[1]))
    except ValueError:
        logger.debug(log_msg)


def _valid_bytes_range(bytes_range):
    length = bytes_range[1] - bytes_range[0] + 1
    if bytes_range[0] < 0 or bytes_range[1] < 1:
        return False
    if length < 2:
        return False
    return True


@app.route('/v1/private_images/<image_id>/layer', methods=['GET'])
@toolkit.requires_auth
@require_completion
def get_private_image_layer(image_id):
    try:
        headers = None
        bytes_range = None
        if store.supports_bytes_range:
            headers['Accept-Ranges'] = 'bytes'
            bytes_range = _parse_bytes_range()
        repository = toolkit.get_repository()
        if not repository:
            # No auth token found, either standalone registry or privileged
            # access. In both cases, private images are "disabled"
            return toolkit.api_error('Image not found', 404)
        if not store.is_private(*repository):
            return toolkit.api_error('Image not found', 404)
        return _get_image_layer(image_id, headers, bytes_range)
    except exceptions.FileNotFoundError:
        return toolkit.api_error('Image not found', 404)


@app.route('/v1/images/<image_id>/layer', methods=['GET'])
@toolkit.requires_auth
@require_completion
@set_cache_headers
@mirroring.source_lookup(cache=True, stream=True)
def get_image_layer(image_id, headers):
    try:
        bytes_range = None
        if store.supports_bytes_range:
            headers['Accept-Ranges'] = 'bytes'
            bytes_range = _parse_bytes_range()
        repository = toolkit.get_repository()
        if repository and store.is_private(*repository):
            return toolkit.api_error('Image not found', 404)
        # If no auth token found, either standalone registry or privileged
        # access. In both cases, access is always "public".
        return _get_image_layer(image_id, headers, bytes_range)
    except exceptions.FileNotFoundError:
        return toolkit.api_error('Image not found', 404)


@app.route('/v1/images/<image_id>/layer', methods=['PUT'])
@toolkit.requires_auth
def put_image_layer(image_id):
    try:
        json_data = store.get_content(store.image_json_path(image_id))
    except exceptions.FileNotFoundError:
        return toolkit.api_error('Image not found', 404)
    layer_path = store.image_layer_path(image_id)
    mark_path = store.image_mark_path(image_id)
    if store.exists(layer_path) and not store.exists(mark_path):
        return toolkit.api_error('Image already exists', 409)
    input_stream = flask.request.stream
    if flask.request.headers.get('transfer-encoding') == 'chunked':
        # Careful, might work only with WSGI servers supporting chunked
        # encoding (Gunicorn)
        input_stream = flask.request.environ['wsgi.input']
    # compute checksums
    csums = []
    sr = toolkit.SocketReader(input_stream)
    if toolkit.DockerVersion() < '0.10':
        tmp, store_hndlr = storage.temp_store_handler()
        sr.add_handler(store_hndlr)
    h, sum_hndlr = checksums.simple_checksum_handler(json_data)
    sr.add_handler(sum_hndlr)
    store.stream_write(layer_path, sr)
    csums.append('sha256:{0}'.format(h.hexdigest()))

    if toolkit.DockerVersion() < '0.10':
        # NOTE(samalba): After docker 0.10, the tarsum is not used to ensure
        # the image has been transfered correctly.
        logger.debug('put_image_layer: Tarsum is enabled')
        tar = None
        tarsum = checksums.TarSum(json_data)
        try:
            tmp.seek(0)
            tar = tarfile.open(mode='r|*', fileobj=tmp)
            tarfilesinfo = layers.TarFilesInfo()
            for member in tar:
                tarsum.append(member, tar)
                tarfilesinfo.append(member)
            layers.set_image_files_cache(image_id, tarfilesinfo.json())
        except (IOError, tarfile.TarError) as e:
            logger.debug('put_image_layer: Error when reading Tar stream '
                         'tarsum. Disabling TarSum, TarFilesInfo. '
                         'Error: {0}'.format(e))
        finally:
            if tar:
                tar.close()
            # All data have been consumed from the tempfile
            csums.append(tarsum.compute())
            tmp.close()

    # We store the computed checksums for a later check
    save_checksums(image_id, csums)
    return toolkit.response()


@app.route('/v1/images/<image_id>/checksum', methods=['PUT'])
@toolkit.requires_auth
def put_image_checksum(image_id):
    if toolkit.DockerVersion() < '0.10':
        checksum = flask.request.headers.get('X-Docker-Checksum')
    else:
        checksum = flask.request.headers.get('X-Docker-Checksum-Payload')
    if not checksum:
        return toolkit.api_error('Missing Image\'s checksum')
    if not store.exists(store.image_json_path(image_id)):
        return toolkit.api_error('Image not found', 404)
    mark_path = store.image_mark_path(image_id)
    if not store.exists(mark_path):
        return toolkit.api_error('Cannot set this image checksum', 409)
    checksums = load_checksums(image_id)
    if checksum not in checksums:
        logger.debug('put_image_checksum: Wrong checksum. '
                     'Provided: {0}; Expected: {1}'.format(
                         checksum, checksums))
        return toolkit.api_error('Checksum mismatch')
    # Checksum is ok, we remove the marker
    store.remove(mark_path)
    # We trigger a task on the diff worker if it's running
    layers.enqueue_diff(image_id)
    return toolkit.response()


@app.route('/v1/private_images/<image_id>/json', methods=['GET'])
@toolkit.requires_auth
@require_completion
def get_private_image_json(image_id):
    repository = toolkit.get_repository()
    if not repository:
        # No auth token found, either standalone registry or privileged access
        # In both cases, private images are "disabled"
        return toolkit.api_error('Image not found', 404)
    try:
        if not store.is_private(*repository):
            return toolkit.api_error('Image not found', 404)
        return _get_image_json(image_id)
    except exceptions.FileNotFoundError:
        return toolkit.api_error('Image not found', 404)


@app.route('/v1/images/<image_id>/json', methods=['GET'])
@toolkit.requires_auth
@require_completion
@set_cache_headers
@mirroring.source_lookup(cache=True, stream=False)
def get_image_json(image_id, headers):
    try:
        repository = toolkit.get_repository()
        if repository and store.is_private(*repository):
            return toolkit.api_error('Image not found', 404)
        # If no auth token found, either standalone registry or privileged
        # access. In both cases, access is always "public".
        return _get_image_json(image_id, headers)
    except exceptions.FileNotFoundError:
        return toolkit.api_error('Image not found', 404)


@app.route('/v1/images/<image_id>/ancestry', methods=['GET'])
@toolkit.requires_auth
@require_completion
@set_cache_headers
@mirroring.source_lookup(cache=True, stream=False)
def get_image_ancestry(image_id, headers):
    ancestry_path = store.image_ancestry_path(image_id)
    try:
        # Note(dmp): unicode patch
        data = store.get_json(ancestry_path)
    except exceptions.FileNotFoundError:
        return toolkit.api_error('Image not found', 404)
    return toolkit.response(data, headers=headers)


def check_images_list(image_id):
    if cfg.disable_token_auth is True or cfg.standalone is True:
        # We enforce the check only when auth is enabled so we have a token.
        return True
    repository = toolkit.get_repository()
    try:
        path = store.images_list_path(*repository)
        # Note(dmp): unicode patch
        images_list = store.get_json(path)
    except exceptions.FileNotFoundError:
        return False
    return (image_id in images_list)


def save_checksums(image_id, checksums):
    for checksum in checksums:
        checksum_parts = checksum.split(':')
        if len(checksum_parts) != 2:
            return 'Invalid checksum format'
    # We store the checksum
    checksum_path = store.image_checksum_path(image_id)
    store.put_content(checksum_path, json.dumps(checksums))


def load_checksums(image_id):
    checksum_path = store.image_checksum_path(image_id)
    data = store.get_content(checksum_path)
    try:
        # Note(dmp): unicode patch NOT applied here
        return json.loads(data)
    except ValueError:
        # NOTE(sam): For backward compatibility only, existing data may not be
        # a valid json but a simple string.
        return [data]


@app.route('/v1/images/<image_id>/json', methods=['PUT'])
@toolkit.requires_auth
def put_image_json(image_id):
    data = None
    try:
        # Note(dmp): unicode patch
        data = json.loads(flask.request.data.decode('utf8'))
    except ValueError:
        pass
    if not data or not isinstance(data, dict):
        return toolkit.api_error('Invalid JSON')
    if 'id' not in data:
        return toolkit.api_error('Missing key `id\' in JSON')
    if image_id != data['id']:
        return toolkit.api_error('JSON data contains invalid id')
    if check_images_list(image_id) is False:
        return toolkit.api_error('This image does not belong to the '
                                 'repository')
    parent_id = data.get('parent')
    if parent_id and not store.exists(store.image_json_path(data['parent'])):
        return toolkit.api_error('Image depends on a non existing parent')
    elif parent_id and not toolkit.validate_parent_access(parent_id):
        return toolkit.api_error('Image depends on an unauthorized parent')
    json_path = store.image_json_path(image_id)
    mark_path = store.image_mark_path(image_id)
    if store.exists(json_path) and not store.exists(mark_path):
        return toolkit.api_error('Image already exists', 409)
    # If we reach that point, it means that this is a new image or a retry
    # on a failed push
    store.put_content(mark_path, 'true')
    # We cleanup any old checksum in case it's a retry after a fail
    try:
        store.remove(store.image_checksum_path(image_id))
    except Exception:
        pass
    store.put_content(json_path, flask.request.data)
    layers.generate_ancestry(image_id, parent_id)
    return toolkit.response()


@app.route('/v1/private_images/<image_id>/files', methods=['GET'])
@toolkit.requires_auth
@require_completion
def get_private_image_files(image_id, headers):
    repository = toolkit.get_repository()
    if not repository:
        # No auth token found, either standalone registry or privileged access
        # In both cases, private images are "disabled"
        return toolkit.api_error('Image not found', 404)
    try:
        if not store.is_private(*repository):
            return toolkit.api_error('Image not found', 404)
        data = layers.get_image_files_json(image_id)
        return toolkit.response(data, headers=headers, raw=True)
    except exceptions.FileNotFoundError:
        return toolkit.api_error('Image not found', 404)
    except tarfile.TarError:
        return toolkit.api_error('Layer format not supported', 400)


@app.route('/v1/images/<image_id>/files', methods=['GET'])
@toolkit.requires_auth
@require_completion
@set_cache_headers
def get_image_files(image_id, headers):
    try:
        repository = toolkit.get_repository()
        if repository and store.is_private(*repository):
            return toolkit.api_error('Image not found', 404)
        # If no auth token found, either standalone registry or privileged
        # access. In both cases, access is always "public".
        data = layers.get_image_files_json(image_id)
        return toolkit.response(data, headers=headers, raw=True)
    except exceptions.FileNotFoundError:
        return toolkit.api_error('Image not found', 404)
    except tarfile.TarError:
        return toolkit.api_error('Layer format not supported', 400)


@app.route('/v1/images/<image_id>/diff', methods=['GET'])
@toolkit.requires_auth
@require_completion
@set_cache_headers
def get_image_diff(image_id, headers):
    try:
        if not cache.redis_conn:
            return toolkit.api_error('Diff queue is disabled', 400)
        repository = toolkit.get_repository()
        if repository and store.is_private(*repository):
            return toolkit.api_error('Image not found', 404)

        # first try the cache
        diff_json = layers.get_image_diff_cache(image_id)
        # it the cache misses, request a diff from a worker
        if not diff_json:
            layers.diff_queue.push(image_id)
            # empty response
            diff_json = ""

        return toolkit.response(diff_json, headers=headers, raw=True)
    except exceptions.FileNotFoundError:
        return toolkit.api_error('Image not found', 404)
    except tarfile.TarError:
        return toolkit.api_error('Layer format not supported', 400)
