Docker-Registry
===============

Create the configuration
------------------------

```
$ cp config_sample.yml config.yml
```

Edit the configuration with your information.

Each key in the configuration (except "common") is flavor. You can specify the flavor by setting the environment
variable "SETTINGS_FLAVOR". If there is no variable set, the default one is "dev".

Run the Registry
----------------

```
pip install -r requirements.txt
./wsgi.py
```

The recommended setting to run the Registry in a prod environment is gunicorn behind a nginx server which supports
chunked transfer-encoding (nginx >= 1.3.9).

```
gunicorn -b 0.0.0.0:5000 -w 1 wsgi:application
```

Run tests
---------

```
$ cd test
$ python -m unittest discover
```

The file test_workflow.py is bit special since it's a functional test (not a
unit test). It requires a server to be running in order to succeed.

```
$ ./wsgi.py
$ DOCKER_CREDS="user:password" python -m unittest test_workflow
```

DOCKER_CREDS contains user credentials information to connect to the staging
index server.

Code coverage
-------------

Using nosetests with coverage.py:

```
$ nosetests --with-coverage
$ coverage html --include="${PWD}/*"
$ cd htmlcov ; python -m SimpleHTTPServer

# open browser http://localhost:8000
```
