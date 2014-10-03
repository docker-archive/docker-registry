# Docker Registry (golang implementation)

## Requirements

You need to have docker >= 0.5.0 up and running.

## Limitations

This implementation doesn't provide all the features that are available in the Python implementation of the Docker Registry.

## Build and start docker image for registry

    $ git clone https://github.com/docker/docker-registry.git docker-registry.git
    $ cd docker-registry.git/contrib/golang_impl
    $ docker build -t docker_registry/golang .
    $ docker run -v /data:/data -d -p 80:80 docker_registry/golang

__Notice__: -p 80:80 binds the registry to your local port 80. This is necessary because it seems you currently cannot delete images where
the tag includes a port.

## Test / Use

### Push test image to registry
    
    $ docker build -t 127.0.0.1/test/test - << EOF
    FROM ubuntu
    RUN echo world > /hello
    CMD cat /hello
    EOF

    $ docker push 127.0.0.1/test/test

### Delete local registry image

    $ docker rmi 127.0.0.1/test/test

### Run test image

    $ docker run 127.0.0.1/test/test

Now the image is fetched from your local registry and executed. Should print out `world`.
