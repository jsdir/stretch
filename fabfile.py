import os
from fabric.api import local

local_dir = os.path.dirname(os.path.realpath(__file__))

def test():
    local('%s test --rednose' % os.path.join(local_dir, 'manage.py'))
