#!/usr/bin/env python
import os
from setuptools import setup, find_packages

import stretch


def read(file_name):
    return open(file_name).read()


setup(
    name='stretch',
    version=stretch.__version__,
    description='A private PaaS powered by docker',
    long_description=read('README.md'),
    packages=find_packages(exclude=['tests', 'client']),
    install_requires=read('requirements.txt').splitlines(),
    entry_points={
        'console_scripts': [
            'stretch = stretch.commands:run',
        ]
    }
)
