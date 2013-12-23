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

NOTE: it's possible to load environment variables from the config file
with a simple syntax: _env:VARIABLENAME. Check this syntax in action
in the example below...


#### Example config

```yaml

common:
    loglevel: info

prod:
    loglevel: warn
    storage: s3
    s3_access_key: _env:AWS_S3_ACCESS_KEY
    s3_secret_key: _env:AWS_S3_SECRET_KEY
    s3_bucket: _env:AWS_S3_BUCKET
    storage_path: /srv/docker
    smtp_host: localhost
    from_addr: docker@myself.com
    to_addr: my@myself.com

dev:
    loglevel: debug
    storage: local
    storage_path: /home/myself/docker

test:
    storage: local
    storage_path: /tmp/tmpdockertmp
```    


Location of the config file
===========================

### DOCKER_REGISTRY_CONFIG

Specify the config file to be used by setting `DOCKER_REGISTRY_CONFIG` in your 
environment: `export DOCKER_REGISTRY_CONFIG=config.yml`

The default location of the config file is `config.yml`, located in the source 
directory.


Available configuration options
===============================

### General options

1. `secret_key`: 64 character string, this key should be unique and secret. It
    is used by the Registry to sign secret things. If you leave this blank, the
    Registry will generate a random string.
1. `loglevel`: string, level of debugging. Any of python's
    [logging](http://docs.python.org/2/library/logging.html) module levels:
    `debug`, `info`, `warn`, `error` or `critical`

### Authentication options

1. `standalone`: boolean, run the server in stand-alone mode. This means that
   the Index service on index.docker.io will not be used for anything. This 
   implies `disable_token_auth`.

1. `index_endpoint`: string, configures the hostname of the Index endpoint.
   This is used to verify passwords of users that log in. It defaults to
   https://index.docker.io. You should probably leave this to its default.

1. `disable_token_auth`: boolean, disable checking of tokens with the Docker
   index. You should provide your own method of authentication (such as Basic
   auth).

### S3 options

These options configure your S3 storage. These are used when `storage` is set
to `s3`.

1. `s3_access_key`: string, S3 access key
1. `s3_secret_key`: string, S3 secret key
1. `s3_bucket`: string, S3 bucket name
1. `s3_encrypt`: boolean, if true, the container will be encrypted on the 
      server-side by S3 and will be stored in an encrypted form while at rest 
      in S3.
1. `s3_secure`: boolean, true for HTTPS to S3
1. `boto_bucket`: string, the bucket name
1. `storage_path`: string, the sub "folder" where image data will be stored.

### Email options

Settings these options makes the Registry send an email on each code Exception:

1. `email_exceptions`:
  1. `smtp_host`: hostname to connect to using SMTP
  1. `smtp_login`: username to use when connecting to authenticated SMTP
  1. `smtp_password`: password to use when connecting to authenticated SMTP
  1. `from_addr`: email address to use when sending email
  1. `to_addr`: email address to send exceptions to

Example:

```yaml
test:
    email_exceptions:
        smtp_host: localhost
```

### Performance on prod

It's possible to add an LRU cache to access small files. In this case you need
to spawn a [redis-server](http://redis.io/) configured in
[LRU mode](http://redis.io/topics/config). The config file "config_sample.yml"
shows an example to enable the LRU cache using the config directive `cache_lru`.

Once this feature is enabled, all small files (tags, meta-data) will be cached
in Redis. When using a remote storage backend (like Amazon S3), it will speeds
things up dramatically since it will reduce roundtrips to S3.


### Storage options

`storage`: can be one of:

1. `local`: store images on local storage
  1. `storage_path` local path to the image store
1. `s3`: store images on S3
  1. `storage_path` is a subdir in your S3 bucker
  1. remember to set all `s3_*` options (see above)
1. `glance`: store images on Glance (OpenStack)
  1. `storage_alternate`: storage engine to use when Glance storage fails, 
      e.g. `local`
  1. If you use `storage_alternate` local, remeber to set `storage_path`

#### Persist local storage

If you use any type of local store along with a registry running within a docker
remember to use a data volume for the `storage_path`. Please read the documentation
for [data volumes](http://docs.docker.io/en/latest/use/working_with_volumes/) for more information. 

Example:

```
docker run -p 5000 -v /tmp/registry:/tmp/registry stackbrew/registry 
```

### Privileged access

Privileged access allows you to make direct requests to the registry by using 
an RSA key pair. The `privileged_key` config entry, if set, must indicate a 
path to a file containing the public key.
If it is not set, privileged access is disabled.

#### Generating keys with `openssl`

Generate private key:

    openssl genrsa  -out private.pem 2048

Associated public key:

    openssl rsa -in private.pem -out public.pem -outform PEM -pubout

Run the Registry
----------------

### The fast way:

```
docker run -p 5000 stackbrew/registry
```

NOTE: The container will try to allocate the port 5000 by default, if the port
is already taken, find out which one has been taken by running "docker ps"

### The old way:

#### On Ubuntu

Install the system requirements for building a Python library:

```
sudo apt-get install build-essential python-dev libevent-dev python-pip libssl-dev
```

Then install the Registry app:

```
sudo pip install -r requirements.txt
```

#### On Red Hat-based systems:

```
sudo yum install python-devel libevent-devel python-pip openssl-devel
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

The recommended setting to run the Registry in a prod environment is gunicorn 
behind a nginx server which supports chunked transfer-encoding (nginx >= 1.3.9).

You could use for instance supervisord to spawn the registry with 8 workers 
using this command:

```
gunicorn -k gevent --max-requests 100 --graceful-timeout 3600 -t 3600 -b localhost:5000 -w 8 wsgi:application
```

Note that when using multiple workers, the secret_key for the Flask session 
must be set explicitly in config.yml. Otherwise each worker will use its own 
random secret key, leading to unpredictable behavior.


#### nginx

[Here is an nginx configuration file example.](https://github.com/dotcloud/docker-registry/blob/master/contrib/nginx.conf)

And you might want to add 
[Basic auth on Nginx](http://wiki.nginx.org/HttpAuthBasicModule) to protect it
(if you're not using it on your local network):


#### Apache

Enable mod_proxy using `a2enmod proxy_http`, then use this snippet forward 
requests to the Docker Registry:

```
  ProxyPreserveHost  On
  ProxyRequests      Off
  ProxyPass          /  http://localhost:5000/
  ProxyPassReverse   /  http://localhost:5000/
```


#### dotCloud

The central Registry runs on the dotCloud platform:

```
cd docker-registry/
dotcloud create myregistry
dotcloud push
```


Run tests
---------

If you want to submit a pull request, please run the unit tests using tox 
before submitting anything to the repos:

```
pip install tox
cd docker-registry/
tox
```
