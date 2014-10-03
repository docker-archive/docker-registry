# VERSION 0.1
# DOCKER-VERSION  0.7.3
# AUTHOR:         Sam Alba <sam@docker.com>
# DESCRIPTION:    Image with docker-registry project and dependecies
# TO_BUILD:       docker build -rm -t registry .
# TO_RUN:         docker run -p 5000:5000 registry

# Latest Ubuntu LTS
from    ubuntu:14.04

# Update
run apt-get update
run apt-get -y upgrade

# Install pip
run apt-get -y install python-pip

# Install deps for backports.lzma (python2 requires it)
run apt-get -y install python-dev liblzma-dev libevent1-dev

add . /docker-registry
add ./config/boto.cfg /etc/boto.cfg

# Install core
run pip install /docker-registry/depends/docker-registry-core

# Install registry
run pip install file:///docker-registry#egg=docker-registry[bugsnag,newrelic,cors]

env DOCKER_REGISTRY_CONFIG /docker-registry/config/config_sample.yml
env SETTINGS_FLAVOR dev

expose 5000

cmd exec docker-registry
