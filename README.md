Docker-Registry
===============

[![Build Status](https://travis-ci.org/dotcloud/docker-registry.png)](https://travis-ci.org/dotcloud/docker-registry)

About this document
===================

As the documentation evolves with different registry versions, be sure that before reading any further you do:

 * check which version of the registry you are running
 * switch to the corresponding tag to access the README that matches your product version

The stable, released version is currently the [0.7.3 tag](https://github.com/dotcloud/docker-registry/tree/0.7.3).


Quick start
===========

The fastest way to get running:

 * install docker according to the [following instructions](http://docs.docker.io/installation/#installation)
 * run the registry: `docker run -p 5000:5000 registry`

That will use the
[official image from the Docker index](https://index.docker.io/_/registry/).

Here is another example that will launch a container on port 5000, and store images in an Amazon S3 bucket:  
```
docker run \
         -e SETTINGS_FLAVOR=s3 \
         -e AWS_BUCKET=acme-docker \
         -e STORAGE_PATH=/registry \
         -e AWS_KEY=AKIAHSHB43HS3J92MXZ \
         -e AWS_SECRET=xdDowwlK7TJajV1Y7EoOZrmuPEJlHYcNP2k4j49T \
         -e SEARCH_BACKEND=sqlalchemy \
         -p 5000:5000 \
         registry
```

See [config_sample.yml](config/config_sample.yml) for all available environment variables.

Create the configuration
========================

The Docker Registry comes with a sample configuration file,
`config_sample.yml`. Copy this to `config.yml` to provide a basic
configuration:

```
cp config/config_sample.yml config/config.yml
```

Configuration flavors
=====================

Docker Registry can run in several flavors. This enables you to run it
in development mode, production mode or your own predefined mode.

In the `config_sample.yml` file, you'll see several sample flavors:

1. `common`: used by all other flavors as base settings
1. `local`: stores data on the local filesystem
1. `s3`: stores data in an AWS S3 bucket
1. `dev`: basic configuration using the `local` flavor
1. `test`: used by unit tests
1. `prod`: production configuration (basically a synonym for the `s3` flavor)
1. `gcs`: stores data in Google cloud storage
1. `swift`: stores data in OpenStack Swift
1. `glance`: stores data in OpenStack Glance, with a fallback to local storage
1. `glance-swift`: stores data in OpenStack Glance, with a fallback to Swift
1. `elliptics`: stores data in Elliptics key/value storage

You can define your own flavors by adding a new top-level yaml key.

You can specify which flavor to run by setting `SETTINGS_FLAVOR` in your
environment: `export SETTINGS_FLAVOR=dev`

The default flavor is `dev`.

NOTE: it's possible to load environment variables from the config file
with a simple syntax: `_env:VARIABLENAME[:DEFAULT]`. Check this syntax
in action in the example below...


#### Example config

```yaml

common:
    loglevel: info
    search_backend: "_env:SEARCH_BACKEND:"
    sqlalchemy_index_database:
        "_env:SQLALCHEMY_INDEX_DATABASE:sqlite:////tmp/docker-registry.db"

prod:
    loglevel: warn
    storage: s3
    s3_access_key: _env:AWS_S3_ACCESS_KEY
    s3_secret_key: _env:AWS_S3_SECRET_KEY
    s3_bucket: _env:AWS_S3_BUCKET
    boto_bucket: _env:AWS_S3_BUCKET
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

The default location of the config file is `config.yml`, located in
the `config` subdirectory.  If `DOCKER_REGISTRY_CONFIG` is a relative
path, that path is expanded relative to the `config` subdirectory.

### Docker image
When building an image using the Dockerfile or using an image from the
[Docker index](https://index.docker.io/_/registry/), the default config is
`config_sample.yml`.

It is also possible to mount the configuration file into the docker image

```
sudo docker run -p 5000:5000 -v /home/user/registry-conf:/registry-conf -e DOCKER_REGISTRY_CONFIG=/registry-conf/config.yml registry
```

Available configuration options
===============================

When using the `config_sample.yml`, you can pass all options through as environment variables. See [`config_sample.yml`](config/config_sample.yml) for the mapping.

## General options

1. `loglevel`: string, level of debugging. Any of python's
   [logging](http://docs.python.org/2/library/logging.html) module levels:
   `debug`, `info`, `warn`, `error` or `critical`
1. `storage_redirect`: Redirect resource requested if storage engine supports
   this, e.g. S3 will redirect signed URLs, this can be used to offload the
   server.
1. `boto_host`/`boto_port`: If you are using `storage: s3` the
   [standard boto config file locations](http://docs.pythonboto.org/en/latest/boto_config_tut.html#details)
   (`/etc/boto.cfg, ~/.boto`) will be used.  If you are using a
   *non*-Amazon S3-compliant object store, in one of the boto config files'
   `[Credentials]` section, set `boto_host`, `boto_port` as appropriate for the
   service you are using.
1. `bugsnag`: The bugsnag API key (note that if you don't use the official docker container, you need to install the registry with bugsnag enabled: `pip install docker-registry[bugsnag]`)

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

#### Privileged access

1. `privileged_key`: allows you to make direct requests to the registry by using
   an RSA key pair. The value is the path to a file containing the public key.
   If it is not set, privileged access is disabled.

##### Generating keys with `openssl`

You will need to install the python-rsa package (`pip install rsa`) in addition to using `openssl`.
Generating the public key using openssl will lead to producing a key in a format not supported by 
the RSA library the registry is using.

Generate private key:

    openssl genrsa  -out private.pem 2048

Associated public key :

    pyrsa-priv2pub -i private.pem -o public.pem


### Search-engine options

The Docker Registry can optionally index repository information in a
database for the `GET /v1/search` [endpoint][search-endpoint].  You
can configure the backend with a configuration like:

The `search_backend` setting selects the search backend to use.  If
`search_backend` is empty, no index is built, and the search endpoint always
returns empty results.  

1. `search_backend`: The name of the search backend engine to use.
   Currently supported backends are:
   1. `sqlalchemy`

If `search_backend` is neither empty nor one of the supported backends, it
should point to a module.

Example:

```yaml
common:
  search_backend: foo.registry.index.xapian
```

#### sqlalchemy

Use [SQLAlchemy][] as the search backend.

1. `sqlalchemy_index_database`: The database URL passed through to
   [create_engine][].

Example:

```yaml
common:
  search_backend: sqlalchemy
  sqlalchemy_index_database: sqlite:////tmp/docker-registry.db
```

In this case, the module is imported, and an instance of it's `Index`
class is used as the search backend.

### Mirroring Options

All mirror options are placed in a `mirroring` section.

1. `mirroring`:
  1. `source`:
  1. `source_index`:
  1. `tags_cache_ttl`:

Example:

```yaml
common:
  mirroring:
    source: https://registry-1.docker.io
    source_index: https://index.docker.io
    tags_cache_ttl: 172800 # 2 days
```

### Cache options

It's possible to add an LRU cache to access small files. In this case you need
to spawn a [redis-server](http://redis.io/) configured in
[LRU mode](http://redis.io/topics/config). The config file "config_sample.yml"
shows an example to enable the LRU cache using the config directive `cache_lru`.

Once this feature is enabled, all small files (tags, meta-data) will be cached
in Redis. When using a remote storage backend (like Amazon S3), it will speeds
things up dramatically since it will reduce roundtrips to S3.

All config settings are placed in a `cache` or `cache_lru` section.

1. `cache`/`cache_lru`:
  1. `host`: Host address of server
  1. `port`: Port server listens on
  1. `password`: Authentication password


### Email options

Settings these options makes the Registry send an email on each code Exception:

1. `email_exceptions`:
  1. `smtp_host`: hostname to connect to using SMTP
  1. `smtp_port`: port number to connect to using SMTP
  1. `smtp_login`: username to use when connecting to authenticated SMTP
  1. `smtp_password`: password to use when connecting to authenticated SMTP
  1. `smtp_secure`: boolean, true for TLS to using SMTP. this could be a path
                    to the TLS key file for client authentication.
  1. `from_addr`: email address to use when sending email
  1. `to_addr`: email address to send exceptions to

Example:

```yaml
test:
    email_exceptions:
        smtp_host: localhost
```

## Storage options

`storage` selects the storage engine to use. The registry ships with two storage engine by default (`file` and `s3`).

If you want to find other (community provided) storages: `pip search docker-registry-driver`

To use and install one of these alternate storages:

 * `pip install docker-registry-driver-NAME`
 * in the configuration set `storage` to `NAME`
 * add any other storage dependent configuraiton option to the conf file
 * review the storage specific documentation for additional dependency or configuration instructions.

 Currently, we are aware of the following storage driver:

  * [elliptics](https://github.com/noxiouz/docker-registry-driver-elliptics)
  * [swift](https://github.com/bacongobbler/docker-registry-driver-swift)
  * [gcs](https://github.com/dmp42/docker-registry-driver-gcs)
  * [glance](https://github.com/dmp42/docker-registry-driver-glance)

### storage: file

1. `storage_path`: Path on the filesystem where to store data

Example:

```yaml
local:
  storage: file
  storage_path: /mnt/registry
```

#### Persistent storage
If you use any type of local store along with a registry running within a docker
remember to use a data volume for the `storage_path`. Please read the documentation
for [data volumes](http://docs.docker.io/en/latest/use/working_with_volumes/) for more information.

Example:

```
docker run -p 5000 -v /tmp/registry:/tmp/registry registry
```

### storage: s3
AWS Simple Storage Service options

1. `s3_access_key`: string, S3 access key
1. `s3_secret_key`: string, S3 secret key
1. `s3_bucket`: string, S3 bucket name
1. `s3_region`: S3 region where the bucket is located
1. `s3_encrypt`: boolean, if true, the container will be encrypted on the
      server-side by S3 and will be stored in an encrypted form while at rest
      in S3.
1. `s3_secure`: boolean, true for HTTPS to S3
1. `boto_bucket`: string, the bucket name
1. `storage_path`: string, the sub "folder" where image data will be stored.

Example:
```yaml
prod:
  storage: s3
  s3_region: us-west-1
  s3_bucket: acme-docker
  storage_path: /registry
  s3_access_key: AKIAHSHB43HS3J92MXZ
  s3_secret_key: xdDowwlK7TJajV1Y7EoOZrmuPEJlHYcNP2k4j49T
```

Run the Registry
----------------

### Recommended: run the registry docker container

 * install docker according to the [following instructions](http://docs.docker.io/installation/#installation)
 * run the registry: `docker run -p 5000:5000 registry`

or

```
docker run \
         -e SETTINGS_FLAVOR=s3 \
         -e AWS_BUCKET=acme-docker \
         -e STORAGE_PATH=/registry \
         -e AWS_KEY=AKIAHSHB43HS3J92MXZ \
         -e AWS_SECRET=xdDowwlK7TJajV1Y7EoOZrmuPEJlHYcNP2k4j49T \
         -e SEARCH_BACKEND=sqlalchemy \
         -p 5000:5000 \
         registry
```

NOTE: The container will try to allocate the port 5000. If the port
is already taken, find out which container is already using it by running `docker ps`

### Advanced: install the registry on an existing server

#### On Ubuntu

Install the system requirements for building a Python library:

```
sudo apt-get install build-essential python-dev libevent-dev python-pip liblzma-dev
```

Then install the Registry app:

```
sudo pip install docker-registry
```

If you need extra requirements, like bugsnag, specify them:

```
sudo pip install docker-registry[bugsnag]
```


(or clone the repository and `pip install .`)

#### On Red Hat-based systems:

Install the required dependencies:
```
sudo yum install python-devel libevent-devel python-pip gcc xz-devel
```

NOTE: On RHEL and CentOS you will need the
[EPEL](http://fedoraproject.org/wiki/EPEL) repostitories enabled. Fedora
should not require the additional repositories.

Then install the Registry app:

```
sudo python-pip install docker-registry[bugsnag]
```

(or clone the repository and `pip install .`)

#### Run it

```
gunicorn --access-logfile - --debug -k gevent -b 0.0.0.0:5000 -w 1 docker_registry.wsgi:application
```

### How do I setup user accounts?

The standalone registry does not provide account management. For simple
access control, you can set up an nginx or Apache frontend with basic
auth enabled (see `contrib/` for examples).

### What about a Production environment?

The recommended setting to run the Registry in a prod environment is gunicorn
behind a nginx server which supports chunked transfer-encoding (nginx >= 1.3.9).

You could use for instance supervisord to spawn the registry with 8 workers
using this command:

```
gunicorn -k gevent --max-requests 100 --graceful-timeout 3600 -t 3600 -b localhost:5000 -w 8 docker_registry.wsgi:application
```

#### nginx

[Here is an nginx configuration file example.](https://github.com/dotcloud/docker-registry/blob/master/contrib/nginx.conf), which applies to versions < 1.3.9 which are compiled with the [HttpChunkinModule](http://wiki.nginx.org/HttpChunkinModule). 

[This is another example nginx configuration file](https://github.com/dotcloud/docker-registry/blob/master/contrib/nginx_1-3-9.conf) that applies to versions of nginx greater than 1.3.9 that have support for the chunked_transfer_encoding directive.

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

For developers
--------------

Read CONTRIBUTE.md

[search-endpoint]: http://docs.docker.com/reference/api/docker-io_api/#search
[SQLAlchemy]: http://docs.sqlalchemy.org/
[create_engine]:
  http://docs.sqlalchemy.org/en/latest/core/engines.html#sqlalchemy.create_engine
