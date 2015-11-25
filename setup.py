#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2014 CoNWeT Lab., Universidad Politécnica de Madrid

# This file is part of OAuth2 CKAN Extension.

# OAuth2 CKAN Extension is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# OAuth2 CKAN Extension is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with OAuth2 CKAN Extension.  If not, see <http://www.gnu.org/licenses/>.

import re

from setuptools import setup, find_packages

from ckanext.oauth2 import __version__, __description__


PYPI_RST_FILTERS = (
    # Remove travis ci badge
    (r'.*travis-ci\.org/.*', ''),
    # Remove pypip.in badges
    (r'.*pypip\.in/.*', ''),
    (r'.*crate\.io/.*', ''),
    (r'.*coveralls\.io/.*', ''),
)


def rst(filename):
    '''
    Load rst file and sanitize it for PyPI.
    Remove unsupported github tags:
     - code-block directive
     - travis ci build badge
    '''
    content = open(filename).read()
    for regex, replacement in PYPI_RST_FILTERS:
        content = re.sub(regex, replacement, content)
    return content


# long_description = '\n'.join((
#     rst('README.md'),
#     rst('CHANGELOG.rst'),
#     ''
# ))

setup(
    name='ckanext-oauth2',
    version=__version__,
    description=__description__,
    long_description='''
    The OAuth2 extension allows site visitors to login through an OAuth2 server.
    ''',
    keywords='CKAN, OAuth2',
    author='Aitor Magán',
    author_email='amagan@conwet.com',
    url='https://github.com/conwetlab/ckanext-oauth2',
    download_url='https://github.com/conwetlab/ckanext-oauth2/tarball/v' + __version__,
    license='',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    namespace_packages=['ckanext'],
    include_package_data=True,
    zip_safe=False,
    setup_requires=[
        'nose>=1.3.0'
    ],
    install_requires=[
        'requests-oauthlib==0.5.0',
    ],
    tests_require=[
        'nose_parameterized==0.3.3',
        'selenium==2.46.0'
    ],
    test_suite='nosetests',
    entry_points={
        'ckan.plugins': [
            'oauth2 = ckanext.oauth2.plugin:OAuth2Plugin',
        ]
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        'Framework :: Pylons',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Session',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Middleware',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Systems Administration :: Authentication/Directory',
    ],
)
