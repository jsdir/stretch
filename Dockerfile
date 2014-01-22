FROM stackbrew/ubuntu:13.10
MAINTAINER Jason Sommer "gatoralli69@gmail.com"


ENV DEBIAN_FRONTEND noninteractive

RUN echo "deb mirror://mirrors.ubuntu.com/mirrors.txt saucy universe" >> /etc/apt/sources.list && apt-get update && apt-get install -y python-pip supervisor libpq-dev python-dev libevent-dev && adduser celery


ADD stretch /usr/share/stretch/master/stretch
ADD setup.py /usr/share/stretch/master/setup.py
ADD README.md /usr/share/stretch/master/README.md
ADD gconfig.py /usr/share/stretch/master/gconfig.py
ADD build/stretch-supervisor.conf /etc/supervisor/conf.d/stretch-supervisor.conf

RUN mkdir -p /var/cache/stretch

RUN cd /usr/share/stretch/master && pip install -e .

EXPOSE 8080
CMD ["/usr/bin/supervisord", "-n"]
