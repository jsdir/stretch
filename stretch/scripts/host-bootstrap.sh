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

# Configure salt-minion
echo "master: ${MASTER}" >> /etc/salt/minion
echo "grains: {'roles': ['stretch-host']}" >> /etc/salt/minion
# TODO: do we need logs?
echo "log_level_logfile: debug" >> /etc/salt/minion
# TODO: actually enforce state on stretch-host and package the state with stretch

# TODO: etcd clustering
# Configure etcd
#cat >> /etc/supervisor/supervisord.conf << EOL
#[program:etcd]
#command=/usr/local/bin/etcd -C {{ etcd_host }} -d /var/etcd-node
#EOL

#supervisorctl reload
#supervisorctl restart etcd

# Use port forwarding until clustering
echo "127.0.0.1 4001 {{ etcd_host_address }} {{ etcd_host_port }}" >> /etc/rinetd.conf
service rinetd restart

# Restart salt-minion
service salt-minion restart

export DEBIAN_FRONTEND=dialog
