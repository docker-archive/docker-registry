# -*- coding: utf-8 -*-

import flask
import flask_cors

from .lib import config
from .lib import index

from . import toolkit
from .app import app


cfg = config.load()

# Enable the search index
if cfg.search_backend:
    INDEX = index.load(cfg.search_backend.lower())
else:
    INDEX = None


@app.route('/v1/search', methods=['GET'])
@flask_cors.cross_origin(methods=['GET'])  # allow all origins (*)
def get_search():
    search_term = flask.request.args.get('q', '')
    if INDEX is None:
        results = []
    else:
        results = INDEX.results(search_term=search_term)
    return toolkit.response({
        'query': search_term,
        'num_results': len(results),
        'results': results,
    })
