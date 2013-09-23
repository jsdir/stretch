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

# Set the hostname
echo ${FQDN} > /etc/hostname
hostname ${FQDN}
{% if domain_name %}domainname ${DOMAINNAME}{% endif %}

echo '127.0.0.1 localhost' > /etc/hosts
echo "127.0.1.1 ${HOSTNAME} ${FQDN}" >> /etc/hosts

# Restart syslog so it starts logging with the right hostname early on.
service rsyslog restart

# Bootstrap salt-minion
apt-get install -y curl
curl -L http://bootstrap.saltstack.org | sh

# Make agent directory
mkdir -p /var/lib/stretch/agent

# Set salt-master
echo "master: ${MASTER}" >> /etc/salt/minion

# Restart salt-minion
service salt-minion restart

export DEBIAN_FRONTEND=dialog
