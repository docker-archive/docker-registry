# -*- coding: utf-8 -*-


def boot(application, config):
    if config and config['origins']:
        try:
            import flask.ext.cors as cors
            for i in config.keys():
                application.config['CORS_%s' % i.upper()] = config[i]
            cors.CORS(application)
        except Exception as e:
            raise Exception('Failed to init cors support %s' % e)
