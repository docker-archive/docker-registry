# -*- coding: utf-8 -*-

import logging
import logging.handlers
import os

try:
    import bugsnag
    import bugsnag.flask
except ImportError as e:
    _bugsnag_import_error = e
    bugsnag = None
import flask

from . import toolkit
from .lib import config

# configure logging prior to subsequent imports which assume
# logging has been configured
cfg = config.load()
logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',
                    level=getattr(logging, cfg.loglevel.upper()))

from .lib import mirroring
from .server import __version__

app = flask.Flask('docker-registry')


@app.route('/_ping')
@app.route('/v1/_ping')
def ping():
    headers = {'X-Docker-Registry-Standalone': cfg.standalone is True}
    if mirroring.is_mirror():
        headers['X-Docker-Registry-Standalone'] = 'mirror'
    return toolkit.response(headers=headers)


@app.route('/')
def root():
    return toolkit.response('docker-registry server ({0}) (v{1})'
                            .format(cfg.flavor, __version__))


@app.after_request
def after_request(response):
    response.headers['X-Docker-Registry-Version'] = __version__
    response.headers['X-Docker-Registry-Config'] = cfg.flavor
    return response


def init():
    # Configure the email exceptions
    info = cfg.email_exceptions
    if info and info.smtp_host:
        mailhost = info.smtp_host
        mailport = info.smtp_port
        if mailport:
            mailhost = (mailhost, mailport)
        smtp_secure = info.smtp_secure
        secure_args = _adapt_smtp_secure(smtp_secure)
        mail_handler = logging.handlers.SMTPHandler(
            mailhost=mailhost,
            fromaddr=info.from_addr,
            toaddrs=[info.to_addr],
            subject='Docker registry exception',
            credentials=(info.smtp_login,
                         info.smtp_password),
            secure=secure_args)
        mail_handler.setLevel(logging.ERROR)
        app.logger.addHandler(mail_handler)
    # Configure bugsnag
    info = cfg.bugsnag
    if info:
        if not bugsnag:
            raise _bugsnag_import_error
        root_path = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                 '..'))
        bugsnag.configure(api_key=info,
                          project_root=root_path,
                          release_stage=cfg.flavor,
                          notify_release_stages=[cfg.flavor],
                          app_version=__version__
                          )
        bugsnag.flask.handle_exceptions(app)


def _adapt_smtp_secure(value):
    """Adapt the value to arguments of ``SMTP.starttls()``

    .. seealso:: <http://docs.python.org/2/library/smtplib.html\
#smtplib.SMTP.starttls>

    """
    if isinstance(value, basestring):
        # a string - wrap it in the tuple
        return (value,)
    if isinstance(value, config.Config):
        assert set(value.keys()) <= set(['keyfile', 'certfile'])
        return (value.keyfile, value.certfile)
    if value:
        return ()


init()
