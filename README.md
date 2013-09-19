Docker-Registry
===============

[![Build Status](https://travis-ci.org/dotcloud/docker-registry.png)](https://travis-ci.org/dotcloud/docker-registry)

Create the configuration
------------------------

The Docker Registry comes with a sample configuration file,
`config_sample.yml`. Copy this to `config.yml` to provide a basic
configuration:
 
```
cp config_sample.yml config.yml
```

Configuration flavors
=====================

Docker Registry can run in several flavors. This enables you to run it
in development mode, production mode or your own predefined mode.

In the config yaml file, you'll see a few sample flavors:

1. `common`: used by all other flavors as base settings
1. `dev`: used for development
1. `prod`: used for production
1. `test`: used by unit tests
1. `openstack`: to integrate with openstack

You can define your own flavors by adding a new top-level yaml key.

You can specify which flavor to run by setting `SETTINGS_FLAVOR` in your
environment: `export SETTINGS_FLAVOR=dev`

The default environment is `dev`.


#### Example config

```yaml

common:
    loglevel: info

prod:
    loglevel: warn
    storage: local
    storage_path: /srv/docker/
    smtp_host: localhost
    from_addr: docker@myself.com
    to_addr: my@myself.com

dev:
    loglevel: debug
    storage: local
    storage_path: /home/myself/docker/

test:
    storage: local
    storage_path: /tmp/tmpdockertmp/
```    


Location of the config file
===========================

### DOCKER_REGISTRY_CONFIG

Specify the config file to be used by setting `DOCKER_REGISTRY_CONFIG` in your 
environment: `export DOCKER_REGISTRY_CONFIG=config.yml`

The location of the yaml file should be relative to the source directory. Absolute 
paths are not yet supported.

The default location of the config file is `config.yml`, located in the source 
directory.


Available configuration options
===============================

### General options

1. `standalone`: boolean, should we run the server as a standalone server?
1. `loglevel`: level of debugging. Any of python's [logging](http://docs.python.org/2/library/logging.html) module levels: `debug`, `info`, `warn`, `error` or `critical`

### S3 options

These options configure your S3 storage. These are used when `storage` is set to `s3`.

1. `s3_access_key`
1. `s3_secret_key`
1. `s3_bucket`
1. `secret_key`

### Email options

Settings these options makes the Registry send an email on each code Exception:

1. `smtp_host`: hostname to connect to using SMTP
1. `smtp_login`: username to use when connecting to authenticated SMTP
1. `smtp_password`: password to use when connecting to authenticated SMTP
1. `from_addr`: email address to use when sending email
1. `to_addr`: email address to send exceptions to

### Storage options

`storage`: can be one of:

1. `local`: store images on local storage
  1. `storage_path` local path to the image store
1. `s3`: store images on S3
  1. `storage_path` is a subdir in your S3 bucker
  1. remember to set all `s3_*` options (see above)
1. `glance`: store images on Glance (OpenStack)
  1. `storage_alternate`: storage engine to use when Glance storage fails, e.g. `local`
  1. If you use `storage_alternate` local, remeber to set `storage_path`


Run the Registry
----------------

### The fast way:

```
docker run samalba/docker-registry
```

NOTE: The container will try to allocate the port 5000 by default, if the port
is already taken, find out which one has been taken by running "docker ps"

### The old way:

#### On Ubuntu

Install the system requirements for building a Python library:

```
sudo apt-get install build-essential python-dev libevent-dev python-pip
```

Then install the Registry app:

```
sudo pip install -r requirements.txt
```

#### On Red Hat-based systems:

```
sudo yum install python-devel libevent-devel python-pip
```

NOTE: On RHEL and CentOS you will need the
[EPEL](http://fedoraproject.org/wiki/EPEL) repostitories enabled. Fedora
should not require the additional repositories.

Then install the Registry app:

```
sudo python-pip install -r requirements.txt
```

#### Run it

```
gunicorn --access-logfile - --debug -k gevent -b 0.0.0.0:5000 -w 1 wsgi:application
```

### How do I setup user accounts?

The first time someone tries to push to your registry, it will prompt
them for a username, password, and email.

### What about a Production environment?

The recommended setting to run the Registry in a prod environment is gunicorn behind a nginx server which supports
chunked transfer-encoding (nginx >= 1.3.9).

You could use for instance supervisord to spawn the registry with 8 workers using this command:

```
gunicorn -k gevent --max-requests 100 --graceful-timeout 3600 -t 3600 -b localhost:5000 -w 8 wsgi:application
```

Note that when using multiple workers, the secret_key for the Flask session must be set explicitly
in config.yml. Otherwise each worker will use its own random secret key, leading to unpredictable
behavior.

The nginx configuration will look like:

```
location / {
  proxy_pass        http://localhost:5000;
  proxy_set_header  X-Real-IP  $remote_addr;
}
```

And you might want to add [Basic auth on Nginx](http://wiki.nginx.org/HttpAuthBasicModule) to protect it
(if you're not using it on your local network):

NOTE: The central Registry runs on the dotCloud platform:

```
cd docker-registry/
dotcloud create myregistry
dotcloud push
```


Run tests
---------

If you want to submit a pull request, please run the unit tests using tox before submitting anything to the repos:

```
pip install tox
cd docker-registry/
tox
```
