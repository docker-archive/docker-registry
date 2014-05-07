Docker-Registry
===============

[![Build Status](https://travis-ci.org/dotcloud/docker-registry.png)](https://travis-ci.org/dotcloud/docker-registry)

Create the configuration
------------------------

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

It is possible to mount the configuration file into the docker image

```
sudo docker run -p 5000:5000 -v /home/user/registry-conf:/registry-conf -e DOCKER_REGISTRY_CONFIG=/registry-conf/config.yml registry
```

Available configuration options
===============================

### General options

1. `secret_key`: 64 character string, this key should be unique and secret. It
    is used by the Registry to sign secret things. If you leave this blank, the
    Registry will generate a random string.
1. `loglevel`: string, level of debugging. Any of python's
    [logging](http://docs.python.org/2/library/logging.html) module levels:
    `debug`, `info`, `warn`, `error` or `critical`
1. If you are using `storage: s3` the
   [standard boto config file locations](http://docs.pythonboto.org/en/latest/boto_config_tut.html#details)
   (`/etc/boto.cfg, ~/.boto`) will be used.  If you are using a
   *non*-Amazon S3-compliant object store, in one of the boto config files'
   `[Credentials]` section, set `boto_host`, `boto_port` as appropriate for the
   service you are using.
1. `storage_redirect`: Redirect resource requested if storage engine supports
   this, e.g. S3 will redirect signed URLs, this can be used to offload the
   server.

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
1. `s3_region`: S3 region where the bucket is located
1. `s3_encrypt`: boolean, if true, the container will be encrypted on the
      server-side by S3 and will be stored in an encrypted form while at rest
      in S3.
1. `s3_secure`: boolean, true for HTTPS to S3
1. `boto_bucket`: string, the bucket name
1. `storage_path`: string, the sub "folder" where image data will be stored.

### Elliptics options

These options configure your [Elliptics](http://reverbrain.com/elliptics/) storage. These are used when `storage` is set
to `elliptics`.

1. `elliptics_nodes`: Elliptics remotes
1. `elliptics_wait_timeout`: time to wait for the operation complete
1. `elliptics_check_timeout`: timeout for pinging node
1. `elliptics_io_thread_num`: number of IO threads in processing pool
1. `elliptics_net_thread_num`: number of threads in network processing pool
1. `elliptics_nonblocking_io_thread_num`: number of IO threads in processing pool dedicated to nonblocking ops
1. `elliptics_groups`: Elliptics groups registry should use
1. `elliptics_verbosity`: Elliptics logger verbosity (0...4)
1. `elliptics_logfile`: path to Elliptics logfile (default: `dev/stderr`)
1. `elliptics_addr_family`: address family to use when adding Elliptics remotes (default: `2` (for ipv4)). Use 10 for ipv6 remotes on Linux.

Example:
```yaml
dev:
  storage: elliptics
  elliptics_nodes:
      elliptics-host1: 1025
      elliptics-host2: 1025
      ...
      hostN: port
  elliptics_wait_timeout: 60
  elliptics_check_timeout: 60
  elliptics_io_thread_num: 2
  elliptics_net_thread_num: 2
  elliptics_nonblocking_io_thread_num: 2
  elliptics_groups: [1, 2, 3]
  elliptics_verbosity: 4
  elliptics_logfile: "/tmp/logfile.log"
  elliptics_loglevel: debug
```

### Google Cloud Storage options
These options configure your [Google Cloud Storage](https://cloud.google.com/products/cloud-storage/) storage.
These are used when `storage` is set to `gcs`.

1. `boto_bucket`: string, the bucket name
1. `storage_path`: string, the sub "folder" where image data will be stored.
1. `oauth2`: boolean, true to enable [OAuth2.0](https://developers.google.com/accounts/docs/OAuth2)

Example:
```yaml
dev:
  boto_bucket: "_env:GCS_BUCKET"
  storage: gcs
  storage_path: "_env:STORAGE_PATH:/"
  oauth2: true
```

You can also use [developer keys](https://developers.google.com/storage/docs/reference/v1/getting-startedv1#keys) for (if `oauth2` is unset or set to false) instead
of using [OAuth2.0](https://developers.google.com/accounts/docs/OAuth2). Options to configure then:

1. `gs_access_key`: string, GCS access key
1. `gs_secret_key`: string, GCS secret key
1. `gs_secure`: boolean, true for HTTPS to GCS

Example:
```yaml
dev:
  boto_bucket: "_env:GCS_BUCKET"
  storage: gcs
  storage_path: "_env:STORAGE_PATH:/"
  gs_access_key: GOOGTS7C7FUP3AIRVJTE
  gs_secret_key: bGoa+V7g/yqDXvKRqq+JTFn4uQZbPiQJo4pf9RzJ
  gs_secure: false
```

### Search-engine options

The Docker Registry can optionally index repository information in a
database for the `GET /v1/search` [endpoint][search-endpoint].  You
can configure the backend with a configuration like:

```yaml
search_backend: "_env:SEARCH_BACKEND:"
```

The `search_backend` setting selects the search backend to use.  If
`search_backend` is empty, no index is built, and the search endpoint
always returns empty results.  Currently supported backends and their
backend-specific configuration options are:

* `sqlalchemy': Use [SQLAlchemy][].
    * The backing database is selected with
      `sqlalchemy_index_database`, which is passed through to
      [create_engine][].

If `search_backend` is neither empty nor one of the above backends, it
should point to a module:

```yaml
search_backend: foo.registry.index.xapian
```

In this case, the module is imported, and an instance of it's `Index`
class is used as the search backend.

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
  1. `storage_path` is a subdir in your S3 bucket
  1. remember to set all `s3_*` options (see above)
1. `glance`: store images on Glance (OpenStack)
  1. `storage_alternate`: storage engine to use when Glance storage fails,
      e.g. `local`
  1. If you use `storage_alternate` local, remeber to set `storage_path`
1. `elliptics`: store images in [Elliptics](http://reverbrain.com/elliptics/) key-value storage

#### Persist local storage

If you use any type of local store along with a registry running within a docker
remember to use a data volume for the `storage_path`. Please read the documentation
for [data volumes](http://docs.docker.io/en/latest/use/working_with_volumes/) for more information.

Example:

```
docker run -p 5000 -v /tmp/registry:/tmp/registry registry
```

### Privileged access

Privileged access allows you to make direct requests to the registry by using
an RSA key pair. The `privileged_key` config entry, if set, must indicate a
path to a file containing the public key.
If it is not set, privileged access is disabled.

#### Generating keys with `openssl`

You will need to install the python-rsa package (`pip install rsa`) in addition to using `openssl`.
Generating the public key using openssl will lead to producing a key in a format not supported by 
the RSA library the registry is using.

Generate private key:

    openssl genrsa  -out private.pem 2048

Associated public key :

    pyrsa-priv2pub -i private.pem -o public.pem

Run the Registry
----------------

### The fast way:

```
docker run -p 5000:5000 registry
```

NOTE: The container will try to allocate the port 5000. If the port
is already taken, find out which container is already using it by running "docker ps"

### The old way:

#### On Ubuntu

Install the system requirements for building a Python library:

```
sudo apt-get install build-essential python-dev libevent-dev python-pip libssl-dev liblzma-dev libffi-dev
```

Then install the Registry app:

```
sudo pip install .
```

#### On Red Hat-based systems:

Install the required dependencies:
```
sudo yum install python-devel libevent-devel python-pip openssl-devel libffi-devel gcc xz-devel
```

NOTE: On RHEL and CentOS you will need the
[EPEL](http://fedoraproject.org/wiki/EPEL) repostitories enabled. Fedora
should not require the additional repositories.

Then install the Registry app:

```
sudo python-pip install .
```

#### Run it

```
gunicorn --access-logfile - --debug -k gevent -b 0.0.0.0:5000 -w 1 docker_registry.wsgi:application
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
gunicorn -k gevent --max-requests 100 --graceful-timeout 3600 -t 3600 -b localhost:5000 -w 8 docker_registry.wsgi:application
```

Note that when using multiple workers, the secret_key for the Flask session
must be set explicitly in config.yml. Otherwise each worker will use its own
random secret key, leading to unpredictable behavior.


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

Run tests
---------
Make sure you have git installed. If not:

Fedora/RHEL/CentOS :

```
sudo yum install git
```

If you want to submit a pull request, please run the unit tests using tox
before submitting anything to the repos:

```
pip install tox
cd docker-registry/
tox
```

[search-endpoint]:
  http://docs.docker.io/en/latest/reference/api/index_api/#get--v1-search
[SQLAlchemy]: http://docs.sqlalchemy.org/
[create_engine]:
  http://docs.sqlalchemy.org/en/latest/core/engines.html#sqlalchemy.create_engine
