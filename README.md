Docker-Registry
===============

[![Build Status](https://travis-ci.org/docker/docker-registry.png)](https://travis-ci.org/docker/docker-registry)

About this document
===================

As the documentation evolves with different registry versions, be sure that before reading any further you:

 * check which version of the registry you are running
 * switch to the corresponding tag to access the README that matches your product version

The stable, released version is the [0.9.0 tag](https://github.com/docker/docker-registry/tree/0.9.0).

Please also have a quick look at the [FAQ](FAQ.md) before reporting bugs.

# Table of Contents
- [Quick Start](#quick-start)
- [Configuration mechanism overview](#configuration-mechanism-overview)
- [Configuration flavors](#configuration-flavors)
  - [Example config](#example-config)
- [Available configuration options](#available-configuration-options)
  - [General options](#general-options)
    - [Authentication options](#authentication-options)
    - [Search-engine options](#search-engine-options)
      - [sqlalchemy](#sqlalchemy)
    - [Mirroring Options](#mirroring-options)
    - [Cache options](#cache-options)
    - [Storage options](#storage-options)
      - [storage file](#storage-file)
        - [Persistent storage](#persistent-storage)
      - [storage s3](#storage-s3)
- [Your own config](#your-own-config)
- [Advanced use](#advanced-user)
- [Drivers](#drivers)
- [For developers](#for-developers)

# Quick start

The fastest way to get running:

 * [install docker](https://docs.docker.com/installation/#installation)
 * run the registry: `docker run -p 5000:5000 registry`

That will use the [official image from the Docker hub](https://registry.hub.docker.com/_/registry/).

Here is a slightly more complex example that launches a registry on port 5000, using an Amazon S3 bucket to store images with a custom path, and enables the search endpoint:

```
docker run \
         -e SETTINGS_FLAVOR=s3 \
         -e AWS_BUCKET=mybucket \
         -e STORAGE_PATH=/registry \
         -e AWS_KEY=myawskey \
         -e AWS_SECRET=myawssecret \
         -e SEARCH_BACKEND=sqlalchemy \
         -p 5000:5000 \
         registry
```


# Configuration mechanism overview

By default, the registry will use the [config_sample.yml](config/config_sample.yml) configuration to start.

Individual configuration options from that file may be overridden using environment variables. Example: `docker run -e STORAGE_PATH=/registry`.

You may also use different "flavors" from that file (see below).

Finally, you can use your own configuration file (see below).


# Configuration flavors

The registry can be instructed to use a specific flavor from a configuration file.

This mechanism lets you define different running "mode" (eg: "development", "production" or anything else).

In the `config_sample.yml` file, you'll see several sample flavors:

1. `common`: used by all other flavors as base settings
1. `local`: stores data on the local filesystem
1. `s3`: stores data in an AWS S3 bucket
1. `ceph-s3`: stores data in a Ceph cluster via a Ceph Object Gateway, using the S3 API
1. `azureblob`: stores data in an Microsoft Azure Blob Storage ([(docs)](ADVANCED.md))
1. `dev`: basic configuration using the `local` flavor
1. `test`: used by unit tests
1. `prod`: production configuration (basically a synonym for the `s3` flavor)
1. `gcs`: stores data in Google cloud storage
1. `swift`: stores data in OpenStack Swift
1. `glance`: stores data in OpenStack Glance, with a fallback to local storage
1. `glance-swift`: stores data in OpenStack Glance, with a fallback to Swift
1. `elliptics`: stores data in Elliptics key/value storage

You can define your own flavors by adding a new top-level yaml key.

To specify which flavor you want to run, set the `SETTINGS_FLAVOR`
environment variable: `export SETTINGS_FLAVOR=dev`

The default flavor is `dev`.

NOTE: it's possible to load environment variables from within the config file
with a simple syntax: `_env:VARIABLENAME[:DEFAULT]`. Check this syntax
in action in the example below...


## Example config

```yaml

common: &common
    standalone: true
    loglevel: info
    search_backend: "_env:SEARCH_BACKEND:"
    sqlalchemy_index_database:
        "_env:SQLALCHEMY_INDEX_DATABASE:sqlite:////tmp/docker-registry.db"

prod:
    <<: *common
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
    <<: *common
    loglevel: debug
    storage: local
    storage_path: /home/myself/docker

test:
    <<: *common
    storage: local
    storage_path: /tmp/tmpdockertmp
```



# Available configuration options

When using the `config_sample.yml`, you can pass all options through as environment variables. See [`config_sample.yml`](config/config_sample.yml) for the mapping.

## General options

1. `loglevel`: string, level of debugging. Any of python's
   [logging](http://docs.python.org/2/library/logging.html) module levels:
   `debug`, `info`, `warn`, `error` or `critical`
1. `debug`: boolean, make the `/_ping` endpoint output more useful information, such as library versions and host information.
1. `storage_redirect`: Redirect resource requested if storage engine supports
   this, e.g. S3 will redirect signed URLs, this can be used to offload the
   server.
1. `boto_host`/`boto_port`: If you are using `storage: s3` the
   [standard boto config file locations](http://docs.pythonboto.org/en/latest/boto_config_tut.html#details)
   (`/etc/boto.cfg, ~/.boto`) will be used.  If you are using a
   *non*-Amazon S3-compliant object store (such as Ceph), in one of the boto config files'
   `[Credentials]` section, set `boto_host`, `boto_port` as appropriate for the
   service you are using. Alternatively, set `boto_host` and `boto_port` in the config file.

## Authentication options

1. `standalone`: boolean, run the server in stand-alone mode. This means that
   the Index service on index.docker.io will not be used for anything. This
   implies `disable_token_auth`.

1. `index_endpoint`: string, configures the hostname of the Index endpoint.
   This is used to verify passwords of users that log in. It defaults to
   https://index.docker.io. You should probably leave this to its default.

1. `disable_token_auth`: boolean, disable checking of tokens with the Docker
   index. You should provide your own method of authentication (such as Basic
   auth).

## Search-engine options

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

In this case, the module is imported, and an instance of its `Index`
class is used as the search backend.

### sqlalchemy

Use [SQLAlchemy][] as the search backend.

1. `sqlalchemy_index_database`: The database URL passed through to
   [create_engine][].

Example:

```yaml
common:
  search_backend: sqlalchemy
  sqlalchemy_index_database: sqlite:////tmp/docker-registry.db
```

On initialization, the `SQLAlchemyIndex` class checks the database
version.  If the database doesn't exist yet (or does exist, but lacks
a `version` table), the `SQLAlchemyIndex` creates the database and
required tables.  To avoid several Gunicorn workers racing to create
the database, you should launch your registry with
[--preload][gunicorn-preload].  For example:

    $ docker run -e GUNICORN_OPTS=[--preload] -p 5000:5000 registry

## Mirroring Options

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

## Cache options

It's possible to add an LRU cache to access small files. In this case you need
to spawn a [redis-server](http://redis.io/) configured in
[LRU mode](http://redis.io/topics/config). The config file "config_sample.yml"
shows an example to enable the LRU cache using the config directive `cache_lru`.

Once this feature is enabled, all small files (tags, meta-data) will be cached
in Redis. When using a remote storage backend (like Amazon S3), it will speed
things up dramatically since it will reduce roundtrips to S3.

All config settings are placed in a `cache` or `cache_lru` section.

1. `cache`/`cache_lru`:
  1. `host`: Host address of server
  1. `port`: Port server listens on
  1. `password`: Authentication password



## Storage options

`storage` selects the storage engine to use. The registry ships with two storage engine by default (`file` and `s3`).

If you want to find other (community provided) storages: `pip search docker-registry-driver`

To use and install one of these alternate storages:

 * `pip install docker-registry-driver-NAME`
 * in the configuration set `storage` to `NAME`
 * add any other storage dependent configuration option to the conf file
 * review the storage specific documentation for additional dependency or configuration instructions.

 Currently, we are aware of the following storage drivers:

  * [azure](https://github.com/ahmetalpbalkan/docker-registry-driver-azure)
  * [elliptics](https://github.com/noxiouz/docker-registry-driver-elliptics)
  * [swift](https://github.com/bacongobbler/docker-registry-driver-swift)
  * [gcs](https://github.com/dmp42/docker-registry-driver-gcs)
  * [glance](https://github.com/dmp42/docker-registry-driver-glance)
  * [oss](https://github.com/chris-jin/docker-registry-driver-alioss.git)

### storage file

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

### storage s3
AWS Simple Storage Service options

1. `s3_access_key`: string, S3 access key
1. `s3_secret_key`: string, S3 secret key
1. `s3_bucket`: string, S3 bucket name
1. `s3_region`: S3 region where the bucket is located
1. `s3_encrypt`: boolean, if true, the container will be encrypted on the
      server-side by S3 and will be stored in an encrypted form while at rest
      in S3.
1. `s3_secure`: boolean, true for HTTPS to S3
1. `s3_use_sigv4`: boolean, true for USE_SIGV4 (boto_host needs to be set or use_sigv4 will be ignored by boto.)
1. `boto_bucket`: string, the bucket name for *non*-Amazon S3-compliant object store
1. `boto_host`: string, host for *non*-Amazon S3-compliant object store
1. `boto_port`: for *non*-Amazon S3-compliant object store
1. `boto_debug`: for *non*-Amazon S3-compliant object store
1. `boto_calling_format`: string, the fully qualified class name of the boto calling format to use when accessing S3 or a *non*-Amazon S3-compliant object store
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

# Your own config

Start from a copy of [config_sample.yml](config/config_sample.yml).

Then, start your registry with a mount point to expose your new configuration inside the container (`-v /home/me/myfolder:/registry-conf`), and point to it using the `DOCKER_REGISTRY_CONFIG` environment variable:

```
sudo docker run -p 5000:5000 -v /home/me/myfolder:/registry-conf -e DOCKER_REGISTRY_CONFIG=/registry-conf/mysuperconfig.yml registry
```

# Advanced use

For more features and advanced options, have a look at the [advanced features documentation](ADVANCED.md)

# Drivers

For more backend drivers, please read [drivers.md](DRIVERS.md)

# For developers

Read [contributing](CONTRIBUTING.md)

[search-endpoint]: http://docs.docker.com/reference/api/docker-io_api/#search
[SQLAlchemy]: http://docs.sqlalchemy.org/
[create_engine]: http://docs.sqlalchemy.org/en/latest/core/engines.html#sqlalchemy.create_engine
[gunicorn-preload]: http://gunicorn-docs.readthedocs.org/en/latest/settings.html#preload-app

