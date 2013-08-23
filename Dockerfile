FROM ubuntu

RUN sed 's/main$/main universe/' -i /etc/apt/sources.list && apt-get update
RUN apt-get install -y git-core python-pip build-essential python-dev libevent1-dev -y
ADD . /docker-registry

RUN cd /docker-registry && pip install -r requirements.txt
RUN cp --no-clobber /docker-registry/config_sample.yml /docker-registry/config.yml

EXPOSE 5000

CMD cd /docker-registry && ./setup-configs.sh && gunicorn --access-logfile - --debug --max-requests 100 --graceful-timeout 3600 -t 3600 -k gevent -b 0.0.0.0:5000 -w 2 wsgi:application
