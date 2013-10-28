docker-ppa:
  pkgrepo.managed:
    - humanname: Docker PPA
    - ppa: dotcloud/lxc-docker

lxc-docker:
  pkg.installed:
    - require:
      - pkgrepo: docker-ppa

python-pip:
  pkg.installed

docker-py:
  pip.installed:
    - name: docker-py==0.2.0
    - require:
      - pkg: python-pip
      - pkg: lxc-docker

# TODO
# ufw installed
# redirect some < 1024 port to ssh daemon and block external access to :22
