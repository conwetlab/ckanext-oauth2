# -*- coding: utf-8 -*-
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
