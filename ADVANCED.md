# Docker-Registry advanced use



## "extras"

The registry supports additional features (that require additional dependencies) that you may require at install time.

### Installation

If you are using the official registry container, you don't need to do anything, as all extras are installed by default.

If you are using pip, you have to explicitly request the extra you want, using pip extra syntax:

`pip install docker-registry[someextra]`

You can request several different extras at the same time by specifying a coma separated list, eg:

`pip install docker-registry[someextra,anotherextra]`

### Available "extras"

#### "bugsnag"

This enables [bugsnag](https://bugsnag.com) reporter in your registry.

1. `bugsnag`: your bugsnag API key

Note the bugsnag "stage" will be set to the specified configuration "flavor".

#### "newrelic"

This encapsulates your registry inside the new-relic agent.

You need to write a new-relic ini file, then use the following environment variables:

 * `NEW_RELIC_INI` to point to your ini file
 * `NEW_RELIC_STAGE` to specify what stage you want

#### "cors"

To enable [CORS support](http://en.wikipedia.org/wiki/Cross-origin_resource_sharing) on your registry, you need to specify at least the `cors.origins` key in your config.

The complete list of what you can configure is as follow:

```
    cors:
        origins: _env:CORS_ORIGINS
        methods: _env:CORS_METHODS
        headers: _env:CORS_HEADERS:[Content-Type]
        expose_headers: _env:CORS_EXPOSE_HEADERS
        supports_credentials: _env:CORS_SUPPORTS_CREDENTIALS
        max_age: _env:CORS_MAX_AGE
        send_wildcard: _env:CORS_SEND_WILDCARD
        always_send: _env:CORS_ALWAYS_SEND
        automatic_options: _env:CORS_AUTOMATIC_OPTIONS
        vary_header: _env:CORS_VARY_HEADER
        resources: _env:CORS_RESOURCES
```

Note that:

 * the official, docker-operated registry doesn't enable CORS
 * if you enable CORS, it will be available on *all* endpoints
 * you should be careful with CORS as it presents numerous security pitfalls for you and your users in case of misuse/misconfiguration

## Proxying

The recommended setting to run the Registry in a production environment is the official container
behind a nginx server which supports chunked transfer-encoding (nginx >= 1.3.9).

This is especially useful if you want to run standalone and implement your own authentication mechanism.

### nginx

[Here is an nginx configuration file example.](https://github.com/docker/docker-registry/blob/master/contrib/nginx/nginx.conf), which applies to versions < 1.3.9 which are compiled with the [HttpChunkinModule](http://wiki.nginx.org/HttpChunkinModule). 

[This is another example nginx configuration file](https://github.com/docker/docker-registry/blob/master/contrib/nginx/nginx_1-3-9.conf) that applies to versions of nginx greater than 1.3.9 that have support for the chunked_transfer_encoding directive.

And you might want to add
[Basic auth on Nginx](http://nginx.org/en/docs/http/ngx_http_auth_basic_module.html) to protect it
(if you're not using it on your local network):


### Apache

Enable mod_proxy using `a2enmod proxy_http`, then use this snippet forward
requests to the Docker Registry:

```
  ProxyPreserveHost  On
  ProxyRequests      Off
  ProxyPass          /  http://localhost:5000/
  ProxyPassReverse   /  http://localhost:5000/
```


## Alternative uses

If you don't want to run the registry inside a docker container, you may do so by running it directly, as follow:


### Ubuntu

Install the system requirements:

```
sudo apt-get install python-dev libevent-dev python-pip liblzma-dev
```

Then install the Registry app:

```
sudo pip install docker-registry
```

If you need extra requirements (see above), specify them:

```
sudo pip install docker-registry[bugsnag,newrelic,cors]
```

Alternatively, you may clone the github repository and run `pip install .`

### Red Hat-based systems:

Install the required dependencies:

```
sudo yum install python-devel libevent-devel python-pip gcc xz-devel
```

NOTE: On RHEL and CentOS you will need the
[EPEL](http://fedoraproject.org/wiki/EPEL) repositories enabled. Fedora
should not require the additional repositories.

Then install the Registry app:

```
sudo python-pip install docker-registry[bugsnag,newrelic,cors]
```

Alternatively, you may clone the github repository and run `pip install .`

### Run it

```
docker-registry
```


### Advanced start options (NOT recommended)

If you want greater control over gunicorn:

```
gunicorn -c contrib/gunicorn_config.py docker_registry.wsgi:application
```

or even bare

```
gunicorn --access-logfile - --error-logfile - -k gevent -b 0.0.0.0:5000 -w 4 --max-requests 100 docker_registry.wsgi:application
```

## *non*-Amazon S3-compliant object stores (e.g. Ceph and Riak CS)

Example:

```
docker run \
         -e SETTINGS_FLAVOR=s3 \
         -e AWS_BUCKET=mybucket \
         -e STORAGE_PATH=/registry \
         -e AWS_KEY=myawskey \
         -e AWS_SECRET=myawssecret \
         -e SEARCH_BACKEND=sqlalchemy \
         -e AWS_HOST=myowns3.com \
         -e AWS_SECURE=false \
         -e AWS_ENCRYPT=false \
         -e AWS_PORT=80 \
         -e AWS_DEBUG=true \
         -e AWS_CALLING_FORMAT=boto.s3.connection.OrdinaryCallingFormat \
         -p 5000:5000 \
         registry
```
## S3 Storage with Cloudfront
It is possible Cloudfront in tandem with S3 storage, you need to configure Cloudfront to point it to your S3 bucket.

This flavor can be started as:
 ```
docker run \
         -e SETTINGS_FLAVOR=cloudfronts3 \
         -e AWS_BUCKET=mybucket \
         -e STORAGE_PATH=/registry \
         -e AWS_KEY=myawskey \
         -e AWS_SECRET=myawssecret \
         -e SEARCH_BACKEND=sqlalchemy \
         -e AWS_SECURE=false \
         -e AWS_ENCRYPT=false \
         -e AWS_PORT=80 \
         -e AWS_DEBUG=true \
         -e CF_BASE_URL=cloudfront_url
         -e CF_KEYID=cloudfront_key_id
         -e CF_KEYSECRET=cloudfront_private_key
         -p 5000:5000 \
         registry
```
`CF_BASE_URL` is the Cloudfront base URL example: https://abcd.cloudfront.net
`CF_KEYID` is the ID of the Cloudfront keypair you are going to use to sign the URLs so the the registry can 302 to Cloudfront.
`CF_KEYSECRET` is either the private key as string or file location of the private key used to sign the URLS.


## Microsoft Azure Blob Storage

In order to use Microsoft Azure Blob Storage Service, you need to create a
storage account from Azure Management Portal or other management scripts.

In the configuration use `azureblob` flavor.

1. `azure_storage_account_name`: string, storage account name
1. `azure_storage_account_key`: string, storage account key
1. `azure_storage_container`: string, container name to be used or created
1. `azure_use_https`: boolean, (default:true) use HTTPS for communication

Example configuration:

```yaml
prod:
  storage: azureblob
  azure_storage_account_name: contoso
  azure_storage_account_key: Fb8cgp___YOUR_KEY___/o8isRdsuHqrHF==
  azure_storage_container: registry
  azure_use_https: true
```

## Advanced configuration options

### Privileged access

It's possible to allow privileged access to your registry using an RSA key (useful for administration scripts for example).

To do so, specify in your config:

1. `privileged_key`: allows you to make direct requests to the registry by using
   an RSA key pair. The value is the path to a file containing the public key.
   If it is not set, privileged access is disabled.

To generate said key using `openssl`, you will need to install the python-rsa package (`pip install rsa`) in addition to using `openssl`.
Generating the public key using openssl will lead to producing a key in a format not supported by 
the RSA library the registry is using.

Generate private key:

    openssl genrsa  -out private.pem 2048

Associated public key :

    pyrsa-priv2pub -i private.pem -o public.pem


### Email exceptions

Setting these options makes the Registry send an email on each code Exception:

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
