import os
from fabric.api import local, lcd, hide, env

local_dir = os.path.dirname(os.path.realpath(__file__))


def test():
    with hide('status', 'aborts'):
        with lcd(local_dir):
            local('%s test --rednose' % os.path.join(local_dir, 'manage.py'))


def cov():
    env.warn_only = True
    with hide('status', 'aborts'):
        local('coverage run manage.py test --rednose')
        local('coverage report -m')


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

