# Gunicorn config file

import os

reload = debug = bool(os.environ.get('DEBUG', False))

bind = '%s:%s' % (
    os.environ.get('REGISTRY_HOST', '0.0.0.0'),
    os.environ.get('REGISTRY_PORT', '5000')
)
graceful_timeout = int(os.environ.get('GUNICORN_GRACEFUL_TIMEOUT', 3600))
timeout = int(os.environ.get('GUNICORN_SILENT_TIMEOUT', 3600))
worker_class = 'gevent'
max_requests = 100
workers = int(os.environ.get('GUNICORN_WORKERS', 4 if debug else 8))
log_level = 'debug' if debug else 'info'
accesslog = os.environ.get('GUNICORN_ACCESS_LOG_FILE', '-')
errorlog = os.environ.get('GUNICORN_ERROR_LOG_FILE', '-')
access_log_format = ('%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" '
                     '"%(a)s" %(D)s %({X-Docker-Size}o)s')
