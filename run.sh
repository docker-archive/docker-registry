#!/bin/bash
if [[ -z "$GUNICORN_WORKERS" ]] ; then
    GUNICORN_WORKERS=4
fi

if [[ -z "$REGISTRY_PORT" ]] ; then
    REGISTRY_PORT=5000
fi


cd "$(dirname $0)"
gunicorn --access-logfile - --debug --max-requests 100 --graceful-timeout 3600 -t 3600 -k gevent -b 0.0.0.0:$REGISTRY_PORT -w $GUNICORN_WORKERS wsgi:application
