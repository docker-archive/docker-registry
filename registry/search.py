__all__ = ['get_search']

import flask
import simplejson as json

import signals
import storage
import toolkit

from .app import app


store = storage.load()
#index = Index()


class Index (dict):
    """Maintain an index of repository data

    The index is a dictionary.  The keys are
    '{namespace}/{repository}' strings, and the values are description
    strings.  For example:

      index['library/ubuntu'] = 'An ubuntu image...'
    """
    def __init__(self):
        super(Index, self).__init__()
        self.version = 1
        self.load()
        signals.repository_created.connect(self._handler_repository_created)
        signals.repository_updated.connect(self._handler_repository_created)
        signals.repository_deleted.connect(self._handler_repository_deleted)

    def load(self):
        regenerated = False
        try:
            index_content = store.get_content(store.index_path())
        except (OSError, IOError):
            index_data = self._regenerate_index()
            regenerated = True
        else:
            data = json.loads(index_content)
            if data['version'] != self.version:
                raise NotImplementedError(
                    'unrecognized search index version {0}'.format(
                        data['version']))
            index_data = data['index']
        self.clear()
        self.update(index_data)
        if regenerated:
            self.save()

    def save(self):
        index_data = {
            'version': self.version,
            'index': dict(self),
        }
        store.put_content(store.index_path(), json.dumps(index_data))

    def _regenerate_index(self):
        index_data = {}
        description = ''  # TODO(wking): store descriptions
        try:
            namespace_paths = list(
                store.list_directory(path=store.repositories))
        except OSError:
            namespace_paths = []
        for namespace_path in namespace_paths:
            namespace = namespace_path.rsplit('/', 1)[-1]
            try:
                repository_paths = list(
                    store.list_directory(path=namespace_path))
            except OSError:
                repository_paths = []
            for path in repository_paths:
                repository = path.rsplit('/', 1)[-1]
                key = '{0}/{1}'.format(namespace, repository)
                index_data[key] = description
        return index_data

    def _handler_repository_created(
            self, sender, namespace, repository, value):
        key = '{0}/{1}'.format(namespace, repository)
        description = ''  # TODO(wking): store descriptions
        self[key] = description
        self.save()

    def _handler_repository_deleted(self, sender, namespace, repository):
        key = '{0}/{1}'.format(namespace, repository)
        try:
            self.pop(key)
        except KeyError:
            pass
        else:
            self.save()


index = Index()


@app.route('/v1/search', methods=['GET'])
def get_search():
    search_term = flask.request.args.get('q', '')
    results = [
        {
            'name': name,
            'description': description,
        }
        for name, description in index.items()
        if search_term in name
        or search_term in description]
    return toolkit.response({
        'query': search_term,
        'num_results': len(results),
        'results': results,
    })
