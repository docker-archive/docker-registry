Docker-Registry
===============

Create the configuration
------------------------

```
cp config_sample.yml config.yml
```

Edit the configuration with your information.

Each key in the configuration (except "common") is flavor. You can specify the flavor by setting the environment
variable "SETTINGS_FLAVOR". If there is no variable set, the default one is "dev".

Run the Registry
----------------

Install the system requirements for building a Python library:

```
sudo apt-get install build-essential libpython-dev libevent-dev
```

Then install the Registry app:

```
pip install -r requirements.txt
```

And run it (for a dev environment):
```
gunicorn --access-logfile - --debug -k gevent -b 0.0.0.0:5000 -w 1 wsgi:application
```

The recommended setting to run the Registry in a prod environment is gunicorn behind a nginx server which supports
chunked transfer-encoding (nginx >= 1.3.9).

You could use for instance supervisord to spawn the Registry using this command:

```
gunicorn -k gevent --max-requests 100 --graceful-timeout 3600 -t 3600 -b localhost:5000 -w 8 wsgi:application
```

The nginx configuration will look like:

```
location / {
  proxy_pass        http://localhost:5000;
  proxy_set_header  X-Real-IP  $remote_addr;
}
```

And you might want to add [Basic auth on Nginx](http://wiki.nginx.org/HttpAuthBasicModule) to protect it
(if you're not using it on your local network):

Run tests
---------

```
$ cd test
$ python -m unittest discover
```

The file workflow.py is bit special since it's a functional test (not a
unit test). It requires a server to be running in order to succeed.

```
$ DOCKER_CREDS="user:password" python -m unittest workflow
```

DOCKER_CREDS contains user credentials information to connect to the staging
index server.

How to contribute
-----------------

If you want to submit a pull request, an important point is to clear up all flake8 warning you could introduce
(ignore the one about registry/__init__.py).

```
$ pip install flake8
$ find . -name '*.py' -exec flake8 {} \;
```

<!---

Code coverage
-------------

Using nosetests with coverage.py:

```
$ nosetests --with-coverage
$ coverage html --include="${PWD}/*"
$ cd htmlcov ; python -m SimpleHTTPServer

# open browser http://localhost:8000
```

-->
