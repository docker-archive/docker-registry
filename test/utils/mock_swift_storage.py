
'''Monkeypatch Openstack Swift Client for testing'''

import swiftclient

from . import monkeypatch_class


class Connection(swiftclient.client.Connection):

    __metaclass__ = monkeypatch_class

    def __init__(self, authurl=None, user=None, key=None, retries=5,
                 preauthurl=None, preauthtoken=None, snet=False,
                 starting_backoff=1, max_backoff=64, tenant_name=None,
                 os_options=None, auth_version="1", cacert=None,
                 insecure=False, ssl_compression=True):
        # initialize a list of containers
        self._swift_containers = {}

    ''' Create a container '''
    def put_container(self, container, headers=None, response_dict=None):
        self._swift_containers[container] = {}

    ''' Deletes a container '''
    def delete_container(self, container, response_dict=None):
        self._swift_containers.pop(container, None)

    ''' Get a listing of objects for the container. '''
    def get_container(self, container, marker=None, limit=None, prefix=None,
                      delimiter=None, end_marker=None, path=None,
                      full_listing=False):
        lst = []
        for key, value in self._swift_containers[container].iteritems():
            if key.startswith(path):
                lst.append({'name': key})
        return None, lst

    ''' attempt to retrieve an object within a container '''
    def get_object(self, container, obj, resp_chunk_size=None,
                   query_string=None, response_dict=None, headers=None):
        try:
            return None, self._swift_containers[container][obj]
        except KeyError:
            raise IOError("Could not get content")

    ''' Attempt to put the contents into an object within a container '''
    def put_object(self, container, obj, contents, content_length=None,
                   etag=None, chunk_size=None, content_type=None,
                   headers=None, query_string=None, response_dict=None):
        try:
            if chunk_size is not None:
                self._swift_containers[container][obj] = contents.read()
            else:
                self._swift_containers[container][obj] = contents
        except Exception:
            raise IOError("Could not put content")

    def delete_object(self, container, obj, query_string=None,
                      response_dict=None):
        self._swift_containers[container].pop(obj, None)
