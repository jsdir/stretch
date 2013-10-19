#!/bin/bash
export DEBIAN_FRONTEND=noninteractive

# Set variables
HOSTNAME={{ hostname }}
MASTER={{ master }}

{% if domain_name %}
DOMAINNAME={{ domain_name }}
FQDN=${HOSTNAME}.${DOMAINNAME}
{% else %}
FQDN=${HOSTNAME}
{% endif %}

{% if not use_public_network %}
# Disable public interface (eth0)
ifconfig eth0 down
sed -i '/auto eth0/s/^/#/' /etc/network/interfaces
{% endif %}

# Set the hostname
echo ${FQDN} > /etc/hostname
hostname ${FQDN}
{% if domain_name %}domainname ${DOMAINNAME}{% endif %}

echo '127.0.0.1 localhost' > /etc/hosts
echo "127.0.1.1 ${HOSTNAME} ${FQDN}" >> /etc/hosts

# Restart syslog so it starts logging with the right hostname early on.
service rsyslog restart

# Bootstrap salt-minion
apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 7F0CEB10
echo 'deb http://downloads-distro.mongodb.org/repo/ubuntu-upstart dist 10gen' | sudo tee /etc/apt/sources.list.d/mongodb.list
apt-get install -y curl linux-image-extra-`uname -r`
curl -L http://get.docker.io | sh
curl -L http://bootstrap.saltstack.org | sh

# Set salt-master
echo "master: ${MASTER}" >> /etc/salt/minion
echo "grains: {'roles': ['stretch-host']}" >> /etc/salt/minion
echo "log_level_logfile: debug" >> /etc/salt/minion
# TODO: actually enforce state on stretch-host and package the state with stretch

# Restart salt-minion
service salt-minion restart

# Install prerequisites for stretch agent
# TODO: use unix domain socket instead of TCP connection
apt-get install -y ufw
ufw deny 27017
mkdir -p /var/lib/stretch/agent
apt-get install -y python-pip mongodb-10gen
pip install pymongo==2.6.3 Jinja2==2.7 docker-py==0.2.1
# TODO: Implement production-ready process management when Docker supports it
echo "python /var/cache/salt/minion/extmods/modules/stretch.py" >> /etc/rc.local

export DEBIAN_FRONTEND=dialog
