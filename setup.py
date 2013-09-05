#!/usr/bin/env python

import os
from setuptools import setup, find_packages

with open('requirements.txt') as f:
    install_requires = f.read().splitlines()

setup(
    name='stretch',
    version='0.1.0',
    description="A private PaaS.",
    long_description=open('README.md').read(),
    packages=find_packages(),
    install_requires=install_requires
)
