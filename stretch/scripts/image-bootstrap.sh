#!/bin/bash
export DEBIAN_FRONTEND=noninteractive

# Install salt, docker, and etcd
apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 7F0CEB10
echo 'deb http://downloads-distro.mongodb.org/repo/ubuntu-upstart dist 10gen' | sudo tee /etc/apt/sources.list.d/mongodb.list
apt-get install -y curl wget ufw rinetd linux-image-extra-`uname -r`
curl -L http://get.docker.io | sh
curl -L http://bootstrap.saltstack.org | sh

# TODO: etcd clustering 5-9 nodes and rest clients
# !! replace rinetd with supervisor
#cd /tmp
#wget https://github.com/coreos/etcd/releases/download/v0.1.2/etcd-v0.1.2-Linux-x86_64.tar.gz
#tar -xvzf etcd-v0.1.2-Linux-x86_64.tar.gz
#cp etcd-v0.1.2-Linux-x86_64/etcd /usr/local/bin/etcd

# Install prerequisites for stretch agent
# TODO: use unix domain socket instead of TCP connection for mongodb
# ufw enable
ufw deny 27017
mkdir -p /var/lib/stretch/agent
apt-get install -y python-pip mongodb-10gen
pip install docker-py==0.2.2 pymongo==2.6.3 Jinja2==2.7 etcd-py==0.0.5
# TODO: Implement production-ready process management when Docker supports it
# TODO: ensure that rc.local runs on startup
echo "python /var/cache/salt/minion/extmods/modules/stretch.py" >> /etc/rc.local

export DEBIAN_FRONTEND=dialog
