#!/usr/bin/env python
from setuptools import setup


dev_requires = [
    'flake8>=2.0,<2.1',
]

tests_require = [
    'nose>=1.3.0,<1.4.0',
    'django-nose>=1.2,<1.3',
    'rednose==0.4.1',
    'coverage>=3.6,<3.7',
    'mock>=0.8.0',
]

install_requires = [
    'Django>=1.6.1,<1.7',
    'django-celery==3.1.1',
    'celery==3.1.1',
    'gunicorn>=18.0,<19.0',
    'south>=0.8.4,<0.9',
    'GitPython==0.3.2.RC1',
    'watchdog>=0.7.0,<0.8.0',
    'PyYAML>=3.10,<3.11',
    'docker-py>=0.2.3,<0.3.0',
]

# TODO: Get the package from GitHub until stream handling is fixed in 0.2.4
dependency_links = [
    'https://github.com/dotcloud/docker-py/archive/236bb5f09e967880e60fd539feb7b325c482d2fd.zip#egg=docker-py-0.2.4'
]

setup(
    name='stretch',
    version='0.1.0',
    author='Jason Sommer',
    description='A PaaS powered by docker.',
    long_description=open('README.md').read(),
    install_requires=install_requires,
    extras_require={
        'tests': tests_require,
        'dev': dev_requires,
    },
    tests_require=tests_require,
    dependency_links=dependency_links,
    license='MIT',
)
