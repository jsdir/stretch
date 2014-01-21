import os
from fabric.api import local, lcd, hide

local_dir = os.path.dirname(os.path.realpath(__file__))


def test():
    with hide('status', 'aborts'):
        local('%s test --rednose --nologcapture' % os.path.join(local_dir, 'manage.py'))


def cov():
    with hide('status', 'aborts'):
        local('%s test --rednose --nologcapture --with-coverage --cover-package=stretch' % os.path.join(local_dir, 'manage.py'))


def build():
    commit = _get_commit()

    with lcd(local_dir):
        _docker_build('stretch/master', commit)

    with lcd(os.path.join(local_dir, 'agent')):
        _docker_build('stretch/agent', commit)


def _docker_build(image, tag):
    local('docker build -t %s:%s .' % (image, tag))


def _get_commit():
    return local('git rev-parse HEAD', capture=True)
