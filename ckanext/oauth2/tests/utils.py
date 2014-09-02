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

from zope.interface import implements

from repoze.who.interfaces import IIdentifier


def make_environ(https=True, **kwds):
    environ = {}
    environ['wsgi.version'] = (1, 0)
    environ['wsgi.url_scheme'] = 'https' if https else 'http'
    environ['SERVER_NAME'] = 'localhost'
    environ['SERVER_PORT'] = '443' if https else '80'
    environ['REQUEST_METHOD'] = 'GET'
    environ['SCRIPT_NAME'] = ''
    environ['PATH_INFO'] = '/'
    environ.update(kwds)
    return environ


class FakeRememberer(object):
    '''Fake rememberer plugin for testing purposes.'''
    implements(IIdentifier)

    def identify(self, environ):
        return None

    def remember(self, environ, identity):
        return [("X-Fake-Remember", identity["repoze.who.userid"])]

    def forget(self, environ, identity):
        return [("X-Fake-Remember", "")]
