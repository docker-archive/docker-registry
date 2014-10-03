# -*- coding: utf-8 -*-

from . import toolkit
from .app import app
from .lib import config
from .lib import index
from .lib import mirroring
import flask


cfg = config.load()

# Enable the search index
INDEX = index.load(cfg.search_backend.lower())


@app.route('/v1/search', methods=['GET'])
@mirroring.source_lookup(index_route=True, merge_results=True)
def get_search():
    search_term = flask.request.args.get('q', '')
    results = INDEX.results(search_term=search_term)
    return toolkit.response({
        'query': search_term,
        'num_results': len(results),
        'results': results,
    })
