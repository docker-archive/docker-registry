#!/bin/sh

cd "$(dirname $0)"
gunicorn --access-logfile - --debug --max-requests 100 --graceful-timeout 3600 -t 3600 -k gevent -b 0.0.0.0:5000 -w 4 wsgi:application
