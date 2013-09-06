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

Inside the `config.yml` file we can see a selection of configuration
headings called `flavors`: `common`, `dev`, `prod`, etc.

You can specify what flavor to run with the `SETTINGS_FLAVOR`
environment variable.

```
$ export SETTINGS_FLAVOR=prod
```

The `common` flavor overrides and is inherited by all other flavors. If
you don't specify a flavor when running the Docker Registry the `dev`
flavor will be used.

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
