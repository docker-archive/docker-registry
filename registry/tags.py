
import simplejson as json
import storage

from flask import request
from toolkit import response, api_error
from .app import app


store = storage.load()


@app.route('/v1/repositories/<namespace>/<repository>/tags', methods=['GET'])
def get_tags(namespace, repository):
    data = {}
    try:
        for fname in store.list_directory(store.tag_path(namespace, repository)):
            tag_name = fname.split('/').pop()
            if not tag_name.startswith('tag_'):
                continue
            data[tag_name[4:]] = store.get_content(fname)
    except OSError:
        return api_error('Repository not found', 404)
    return response(data)


@app.route('/v1/repositories/<namespace>/<repository>/tags/<tag>', methods=['GET'])
def get_tag(namespace, repository, tag):
    data = None
    try:
        data = store.get_content(store.tag_path(namespace, repository, tag))
    except IOError:
        return api_error('Tag not found', 404)
    return response(json.dumps(data))


@app.route('/v1/repositories/<namespace>/<repository>/tags/<tag>', methods=['PUT'])
def put_tag(namespace, repository, tag):
    data = None
    try:
        data = json.loads(request.data)
    except json.JSONDecodeError:
        pass
    if not data or not isinstance(data, basestring):
        return api_error('Invalid data')
    if not store.exists(store.image_json_path(data)):
        return api_error('Image not found', 404)
    store.put_content(store.tag_path(namespace, repository, tag), data)
    return response()


@app.route('/v1/repositories/<namespace>/<repository>/tags/<tag>', methods=['DELETE'])
def delete_tag(namespace, repository, tag):
    try:
        store.remove(store.tag_path(namespace, repository, tag))
    except OSError:
        return api_error('Tag not found', 404)
    return response()
