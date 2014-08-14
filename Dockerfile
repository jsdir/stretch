FROM stackbrew/ubuntu:13.10

ADD bin /usr/share/stretch/master/bin
ADD stretch /usr/share/stretch/master/stretch
ADD requirements.txt /usr/share/stretch/master/requirements.txt

ENV DEBIAN_FRONTEND noninteractive

RUN echo "deb mirror://mirrors.ubuntu.com/mirrors.txt saucy universe" >> /etc/apt/sources.list && apt-get update

RUN apt-get install -y python-pip supervisor libpq-dev python-dev libevent-dev

RUN cd /usr/share/stretch/master && pip install -r requirements.txt

EXPOSE 80
CMD ["/usr/bin/supervisord", "-n"]
