FROM ubuntu

RUN sed -i 's/main$/main universe/' /etc/apt/sources.list && apt-get update
RUN apt-get install -y git-core python-pip build-essential python-dev libevent1-dev -y
ADD . /docker-registry

RUN cd /docker-registry && pip install -r requirements.txt
RUN cp --no-clobber /docker-registry/config_sample.yml /docker-registry/config.yml
RUN sed -i "s/ secret_key: REPLACEME/ secret_key: $(< /dev/urandom tr -dc A-Za-z0-9 | head -c 32)/" /docker-registry/config.yml

EXPOSE 5000

CMD cd /docker-registry && ./setup-configs.sh && ./run.sh
