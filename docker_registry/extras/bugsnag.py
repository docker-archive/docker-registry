# -*- coding: utf-8 -*-

import os


def boot(application, api_key, flavor, version):
    # Configure bugsnag
    if api_key:
        try:
            import bugsnag
            import bugsnag.flask

            root_path = os.path.abspath(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            bugsnag.configure(api_key=api_key,
                              project_root=root_path,
                              release_stage=flavor,
                              notify_release_stages=[flavor],
                              app_version=version
                              )
            bugsnag.flask.handle_exceptions(application)
        except Exception as e:
            raise Exception('Failed to init bugsnag agent %s' % e)
