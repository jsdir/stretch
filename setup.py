#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import re
import codecs
from setuptools import setup, find_packages


def read(*parts):
    path = os.path.join(os.path.dirname(__file__), *parts)
    with codecs.open(path, encoding='utf-8') as fobj:
        return fobj.read()


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


with open('requirements.txt') as fobj:
    install_requires = fobj.read().splitlines()

with open('requirements-dev.txt') as fobj:
    tests_require = fobj.read().splitlines()

# TODO: Get the package from GitHub until stream handling is fixed in 0.2.4
dependency_links = [
    ('https://github.com/dotcloud/docker-py/archive/'
     '236bb5f09e967880e60fd539feb7b325c482d2fd.zip#egg=docker-py-0.2.4')
]

version = find_version('stretch', '__init__.py')

setup(
    name='stretch',
    packages=find_packages(),
    version=version,
    author='Jason Sommer',
    url='https://github.com/gatoralli/stretch',
    download_url = 'https://github.com/gatoralli/stretch/tarball/%s' % version,
    description='A simple PaaS powered by docker.',
    long_description=open('README.md').read(),
    install_requires=install_requires,
    tests_require=tests_require,
    dependency_links=dependency_links,
    license='MIT',
    include_package_data=True,
    test_suite='nose.collector',
    entry_points={
        'console_scripts': [
            'stretch=stretch.cli:main'
        ]
    }
)
