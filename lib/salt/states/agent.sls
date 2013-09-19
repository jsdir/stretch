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
