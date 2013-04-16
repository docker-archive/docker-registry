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

Code coverage
-------------

Using nosetests with coverage.py:

```
$ nosetests --with-coverage
$ coverage html --include="${PWD}/*"
$ cd htmlcov ; python -m SimpleHTTPServer

# open browser http://localhost:8000
```
