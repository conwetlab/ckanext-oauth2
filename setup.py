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

from setuptools import setup, find_packages

setup(
    name='ckanext-oauth2',
    version='1.0.0',
    description='OAuth2 support for CKAN',
    long_description='''
    The OAuth2 extension allows site visitors to login through an OAuth2 server.
    ''',
    keywords='CKAN, OAuth2',
    author='Aitor Magán',
    author_email='amagan@conwet.com',
    url='https://github.com/conwetlab/ckanext-oauth2',
    download_url='https://github.com/conwetlab/ckanext-oauth2/tarball/v1.0.0',
    license='AGPLv3',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    namespace_packages=['ckanext'],
    include_package_data=True,
    zip_safe=False,
    python_requires='>=3.8',
    install_requires=[
        'requests-oauthlib>=1.3.0',
        'PyJWT>=2.0.0',
    ],
    tests_require=[
        'parameterized',
        'pytest',
    ],
    entry_points={
        'ckan.plugins': [
            'oauth2 = ckanext.oauth2.plugin:OAuth2Plugin',
        ],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Session',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Middleware',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Systems Administration :: Authentication/Directory',
    ],
)
