
import datetime
import flask
import logging

import config
import toolkit


VERSION = '0.6.1'
app = flask.Flask('docker-registry')
cfg = config.load()
loglevel = getattr(logging, cfg.get('loglevel', 'INFO').upper())
logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',
                    level=loglevel)


@app.route('/_ping')
@app.route('/v1/_ping')
def ping():
    return toolkit.response()


@app.route('/')
def root():
    return toolkit.response('docker-registry server ({0})'.format(cfg.flavor))


@app.after_request
def after_request(response):
    response.headers['X-Docker-Registry-Version'] = VERSION
    response.headers['X-Docker-Registry-Config'] = cfg.flavor
    return response


def init():
    # Configure the secret key
    if cfg.secret_key:
        flask.Flask.secret_key = cfg.secret_key
    else:
        flask.Flask.secret_key = toolkit.gen_random_string(64)
    # Set the session duration time to 1 hour
    flask.Flask.permanent_session_lifetime = datetime.timedelta(seconds=3600)
    # Configure the email exceptions
    info = cfg.email_exceptions
    if info:
        import logging
        mail_handler = logging.handlers.SMTPHandler(
            mailhost=info['smtp_host'],
            fromaddr=info['from_addr'],
            toaddrs=[info['to_addr']],
            subject='Docker registry exception',
            credentials=(info['smtp_login'],
                         info['smtp_password']))
        mail_handler.setLevel(logging.ERROR)
        app.logger.addHandler(mail_handler)


init()
