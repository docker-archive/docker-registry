# VERSION 0.1
# DOCKER-VERSION  0.7.3
# AUTHOR:         Sam Alba <sam@docker.com>
# DESCRIPTION:    Image with docker-registry project and dependecies
# TO_BUILD:       docker build -rm -t registry .
# TO_RUN:         docker run -p 5000:5000 registry

FROM ubuntu:13.10

RUN apt-get update; \
    apt-get install -y git-core build-essential python-dev \
    libevent1-dev python-openssl liblzma-dev wget; \
    rm /var/lib/apt/lists/*_*
RUN cd /tmp; wget https://bitbucket.org/pypa/setuptools/raw/bootstrap/ez_setup.py
RUN cd /tmp; python ez_setup.py; easy_install pip; \
    rm ez_setup.py

ADD . /docker-registry
ADD ./config/boto.cfg /etc/boto.cfg

RUN pip install /docker-registry/

ENV DOCKER_REGISTRY_CONFIG /docker-registry/config/config_sample.yml

EXPOSE 5000

CMD cd /docker-registry && ./setup-configs.sh && exec docker-registry
