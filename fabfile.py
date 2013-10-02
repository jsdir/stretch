import os
from fabric.api import local, hide

local_dir = os.path.dirname(os.path.realpath(__file__))


def test():
    with hide('status', 'aborts'):
        local('%s test --rednose --nologcapture' % os.path.join(local_dir, 'manage.py'))


def cov():
    with hide('status', 'aborts'):
        local('%s test --rednose --nologcapture --with-coverage --cover-package=stretch' % os.path.join(local_dir, 'manage.py'))
