# -*- coding: utf-8 -*-

from flask.exceptions import JSONBadRequest
from werkzeug.exceptions import Unauthorized, Forbidden, NotFound, Conflict

class JSONUnauthorized(Unauthorized, JSONBadRequest):
    description = (
        "The server could not verify that you are authorized to access "
        "the URL requested.  You either supplied the wrong credentials (e.g. "
        "a bad password), or your browser doesn't understand how to supply "
        "the credentials required. In case you are allowed to request "
        "the document, please check your user-id and password and try "
        "again."
    )

    def get_headers(self, environ):
        headers = JSONBadRequest.get_headers(self, environ)
        headers.append(('WWW-Authenticate', 'Basic realm="Login Required"'))
        return headers

class JSONForbidden(Forbidden, JSONBadRequest):
    description = (
        "You don't have the permission to access the requested resource. "
        "It is either read-protected or not readable by the server."
    )

class JSONNotFound(NotFound, JSONBadRequest):
    description = (
        "The requested URL was not found on the server."
        "If you entered the URL manually please check your spelling and "
        "try again."
    )

class JSONConflict(Conflict, JSONBadRequest):
    description = (
        "A conflict happened while processing the request.  The resource "
        "might have been modified while the request was being processed."
    )
