# VERSION 0.1
# DOCKER-VERSION  0.7.3
# AUTHOR:         Sam Alba <sam@docker.com>
# DESCRIPTION:    Image with docker-registry project and dependecies
# TO_BUILD:       docker build -rm -t registry .
# TO_RUN:         docker run -p 5000:5000 registry

FROM stackbrew/ubuntu:13.04

RUN sed -i 's/main$/main universe/' /etc/apt/sources.list && apt-get update
RUN apt-get install -y git-core build-essential python-dev \
    libevent1-dev python-openssl liblzma-dev wget
RUN cd /tmp; wget http://python-distribute.org/distribute_setup.py
RUN cd /tmp; python distribute_setup.py; easy_install pip; \
    rm distribute_setup.py
ADD . /docker-registry
ADD ./config/boto.cfg /etc/boto.cfg

RUN cd /docker-registry && pip install -r requirements.txt
RUN cp --no-clobber /docker-registry/config/config_sample.yml /docker-registry/config/config.yml

EXPOSE 5000

CMD cd /docker-registry && ./setup-configs.sh && ./run.sh
