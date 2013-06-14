import config

cfg = config.load().index

if cfg and cfg['enabled']:
  import simplejson as json
  import storage
  import socket

  from flask import request
  from toolkit import response, api_error, requires_auth
  from .app import app


  store = storage.load()
  hostname = socket.gethostname()

# TODO[jigish] add WWW-Authenticate signature and X-Docker-Token
  def generate_headers(repository, access):
    if not cfg['registry_endpoints']:
      return {'X-Docker-Endpoints': hostname,
          'WWW-Authenticate': 'Token signature=omgwtfbbq,repository="{0}",access={1}'.format(repository, access),
          'X-Docker-Token': 'omgwtfbbq'}
    return {'X-Docker-Endpoints': cfg['registry_endpoints'],
        'WWW-Authenticate': 'Token signature=omgwtfbbq,repository="{0}",access={1}'.format(repository, access),
        'X-Docker-Token': 'omgwtfbbq'}


### USER MANAGEMENT ###

  @app.route('/v1/users/', methods=['POST'])
  def post_users():
    data = None
    try:
      data = json.loads(request.data)
    except json.JSONDecodeError:
      return api_error('Error Decoding JSON', 400)
    return response('User Created', 201)

  @app.route('/v1/users', methods=['GET'])
  def get_users():
    return response('OK', 200)

  @app.route('/v1/users/<username>/', methods=['PUT'])
  def put_user():
    return response('', 204)


### USER REPO MANAGEMENT ###

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
    return response('', 200, generate_headers('{0}/{1}'.format(namespace, repository), 'write'))

  @app.route('/v1/repositories/<namespace>/<repository>/', methods=['DELETE'])
  @requires_auth
  def delete_user_repo(namespace, repository):
    try:
      store.remove(store.repo_path(namespace, repository))
    except oserror:
      return api_error('repo not found', 404)
    return response('', 200, generate_headers('{0}/{1}'.format(namespace, repository), 'delete'))


### LIBRARY REPO MANAGEMENT ###

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
    return response('', 200, generate_headers(repository, 'write'))

  @app.route('/v1/repositories/<repository>/', methods=['DELETE'])
  @requires_auth
  def delete_library_repo(repository):
    try:
      store.remove(store.repo_path(repository))
    except oserror:
      return api_error('repo not found', 404)
    return response('', 200, generate_headers(repository, 'delete'))


### USER REPO IMAGE MANAGEMENT ###

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
    store.put_content(store.repo_images_path(namespace, repository), request.data)
    return response('', 204, generate_headers('{0}/{1}'.format(namespace, repository), 'write'))

  @app.route('/v1/repositories/<namespace>/<repository>/images', methods=['GET'])
  @requires_auth
  def get_user_images(namespace, repository):
      data = None
      try:
          data = store.get_content(store.repo_images_path(namespace, repository))
      except IOError:
          return api_error('images not found', 404)
      return response(data, 200, generate_headers('{0}/{1}'.format(namespace, repository), 'read'), True)

# TODO[jigish] is this required?
  @app.route('/v1/repositories/<namespace>/<repository>/images', methods=['DELETE'])
  @requires_auth
  def delete_user_images(namespace, repository):
    try:
      store.remove(store.repo_images_path(namespace, repository))
    except oserror:
      return api_error('images not found', 404)
    return response('', 204, generate_headers('{0}/{1}'.format(namespace, repository), 'delete'))


### LIBRARY REPO IMAGE MANAGEMENT ###

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

# TODO[jigish] is this required?
  @app.route('/v1/repositories/<repository>/images', methods=['DELETE'])
  @requires_auth
  def delete_library_images(repository):
    try:
      store.remove(store.repo_images_path(repository))
    except oserror:
      return api_error('images not found', 404)
    return response('', 204, generate_headers(repository, 'delete'))


### USER REPO AUTH ###

  @app.route('/v1/repositories/<namespace>/<repository>/auth', methods=['PUT'])
  def put_user_repo_auth(namespace, repository):
    return response('OK')


### LIBRARY REPO AUTH ###

  @app.route('/v1/repositories/<repository>/auth', methods=['PUT'])
  def put_library_repo_auth(repository):
    return response('OK')


### SEARCH ###

# TODO[jigish] implement
  @app.route('/v1/search', methods=['GET'])
  def get_search():
    return response('{}')
