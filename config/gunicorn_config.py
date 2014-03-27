## Gunicorn config file

import os
import random
import string

flavor = os.environ.get('SETTINGS_FLAVOR', 'dev')

if flavor == 'dev':
    os.environ['SECRET_KEY'] = ''.join(
        [random.choice(string.ascii_lowercase + string.ascii_uppercase +
         string.digits) for x in range(128)])

reload = True
bind = '0.0.0.0:{0}'.format(os.environ.get('PORT_WWW', 8000))
graceful_timeout = 3600
timeout = 3600
worker_class = 'gevent'
max_requests = 100
workers = 4
log_level = 'debug'
debug = True
accesslog = '-'
access_log_format = ('%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" '
                     '"%(a)s" %(D)s %({X-Docker-Size}o)s')

if flavor == 'prod' or flavor == 'staging':
    reload = False
    workers = 8
    debug = False
    log_level = 'info'
    accesslog = '/var/log/supervisor/access.log'
