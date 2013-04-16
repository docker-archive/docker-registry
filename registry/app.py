# -*- coding: utf-8 -*-

from flask import Flask

import config
from toolkit import response

app = Flask('docker-registry')


@app.before_first_request
def first_request():
    cfg = config.load()
    info = cfg.email_exceptions
    if info:
        import logging
        from logging.handlers import SMTPHandler
        mail_handler = SMTPHandler(mailhost=info['smtp_host'],
                fromaddr=info['from_addr'], toaddrs=[info['to_addr']],
                subject='Docker registry exception',
                credentials=(info['smtp_login'], info['smtp_password']))
        mail_handler.setLevel(logging.ERROR)
#        app.logger.addHandler(mail_handler)


@app.route('/_ping')
def ping():
    return response()


@app.route('/')
def root():
    return response('docker-registry server')
