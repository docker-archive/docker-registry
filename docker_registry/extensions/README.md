# docker-registry extensions

You can further extend the registry behavior by authoring specially crafted Python packages and listening to signals.

## For users

### Word of caution

Installing and running third-party addons usually grant execution privileges and access to sensitive information.
docker-registry extensions are no different, and you need to use caution and to fully understand that said addons once run likely have unlimited access to your configuration, including secrets, certificates, etcetera.

Please give this a think before you run random packages.

### Using an extension

1. Find the extension you are interested in. Usually, a docker container packing that extension is available.
2. Review this extension's configuration settings, edit your configuration file accordingly, and run your registry.


## For developers


### Scaffolding

1. Start a new package (named `foo`)
2. Create whatever module folders you wish (make sure you have an empty `__init__.py` in each folder)
3. Create a setup.py for your package (and then call `python setup.py develop`):

```
setuptools.setup(
    entry_points = {
        'docker_registry.extensions': [
            '[some name] = [your.module]'
        ]
    },
```

`[some name]` is currently ignored but it is a required value.

`[your.module]` is the name of your extension module. It will be imported when the entry point is loaded.

4. Run your registry with DEBUG=true so that gunicorn reloads on file change

### Installing

As soon as your python package is installed on the system, your code will get executed.
The main communication API with the registry is through signals (see below).

As far as your users are concerned, all they have to do should be `pip install my-foo-package` (you may require them to add some specific configuration, including to explicitly enable your extension - see below).

That's it.


### API

This very simple example will print when a tag is created:

```
from docker_registry.lib import signals


def receiver():
    print('I am a tag creation receiver')

signals.tag_created.connect(receiver)

```

You can access configuration options through the config API:

```
from docker_registry.lib import config

myconfig = config.load()
```

That will give you the full configuration. We recommend that you place extension configuration settings in the `extensions` portion of the configuration file, e.g.:

```
extensions:
    my_cool_extension:
        some_key: some_value
```

And you would then reference your configuration options like so:

```
myconfig.extensions.my_cool_extension.some_key
```

For convenience, you may also use the following APIs from core:

```
from docker_registry.core import compat
from docker_registry.core import exceptions
```

(see the code...)

### Versioning and compatibility

Right now there is no versioning strategy (save on core), although we will do our best not to break the API for `signals` and `config`.

Any other docker-registry API should be considered private / unstable, and as a responsible extension author, you should think twice before using said internals...

### Packaging for distribution

The preferred way to package is through pypi.

Your package must depend on `docker-registry-core>=2,<3`

You are strongly encouraged to also provide docker containers for your extension (base it on `FROM registry:latest`), and to give the registry maintainers a ping.
