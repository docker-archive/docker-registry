Docker-Registry
===============

Create the configuration
------------------------

```
$ cp config_sample.yml config.yml
```

Edit the configuration with your information.

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
