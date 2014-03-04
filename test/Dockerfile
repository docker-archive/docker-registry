# VERSION 0.1
# DOCKER-VERSION  0.7.3
# AUTHOR:         Daniel Mizyrycki <daniel@docker.com>
# DESCRIPTION:    Test image with docker-registry project and dependecies
# TO_BUILD:       docker build -rm -t docker-registry-test .
# TO_RUN:         docker run -rm -i -t docker-registry-test

FROM registry
MAINTAINER Daniel Mizyrycki <daniel@docker.com>

# Add docker-registry testing dependencies
RUN apt-get update
RUN apt-get install -y --no-install-recommends libssl-dev libffi-dev
RUN pip install -r /docker-registry/test-requirements.txt
RUN pip install tox==1.6.1

# Mountpoint used to share coverage results
RUN mkdir /data

CMD ["sh", "-c", "/docker-registry/test/dockertest.sh"]
