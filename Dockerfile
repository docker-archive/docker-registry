FROM stackbrew/ubuntu:13.04

RUN sed -i 's/main$/main universe/' /etc/apt/sources.list && apt-get update
RUN apt-get install -y git-core python-pip build-essential python-dev libevent1-dev python-openssl
ADD . /docker-registry

RUN cd /docker-registry && pip install -r requirements.txt
RUN cp --no-clobber /docker-registry/config/config_sample.yml /docker-registry/config/config.yml

EXPOSE 5000

CMD cd /docker-registry && ./setup-configs.sh && ./run.sh
