FROM ubuntu:12.10
MAINTAINER Jason Sommer "gatoralli69@gmail.com"

ADD bin /usr/local/share/stretch-master/bin
ADD stretch /usr/local/share/stretch-master/stretch
ADD requirements.txt /usr/local/share/stretch-master/requirements.txt

ENV DEBIAN_FRONTEND noninteractive

RUN  echo "deb http://archive.ubuntu.com/ubuntu precise universe" >> /etc/apt/sources.list && apt-get update

RUN apt-get install -y python-pip supervisor libpq-dev python-dev libevent-dev

RUN cd /usr/local/share/stretch-master && pip install -r requirements.txt

EXPOSE 80
CMD ["/usr/bin/supervisord", "-n"]
