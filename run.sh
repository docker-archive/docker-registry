#!/bin/bash
if [[ -z "$GUNICORN_WORKERS" ]] ; then
    GUNICORN_WORKERS=4
fi

if [[ -z "$REGISTRY_PORT" ]] ; then
    REGISTRY_PORT=5000
fi

if [[ -z "$GUNICORN_GRACEFUL_TIMEOUT" ]] ; then
    GUNICORN_GRACEFUL_TIMEOUT=3600
fi

if [[ -z "$GUNICORN_SILENT_TIMEOUT" ]] ; then
    GUNICORN_SILENT_TIMEOUT=3600
fi

cd "$(dirname $0)"
gunicorn --access-logfile - --debug --max-requests 100 --graceful-timeout $GUNICORN_GRACEFUL_TIMEOUT -t $GUNICORN_SILENT_TIMEOUT -k gevent -b 0.0.0.0:$REGISTRY_PORT -w $GUNICORN_WORKERS wsgi:application
