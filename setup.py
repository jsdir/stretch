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
    'django-celery>=3.0.11,<3.1.0',
    'Celery==3.1',
    'gunicorn>=18.0,<19.0',
    'south>=0.8.4,<0.9',
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
    license='MIT',
)
