# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
import json

import httpretty

# from sure import expect

from oauthlib.oauth2 import InsecureTransportError

from base64 import b64decode, b64encode

from zope.interface.verify import verifyClass

from repoze.who.interfaces import IIdentifier, IAuthenticator, IChallenger
from repoze.who.config import WhoConfig
# from repoze.who.middleware import PluggableAuthenticationMiddleware

# from webtest import TestApp

from ckanext.oauth2.repozewho import OAuth2Plugin, make_plugin
from ckanext.oauth2.tests.utils import make_environ


WHO_CONFIG = '''
[plugin:oauth2]
use = ckanext.oauth2.repozewho:make_plugin
authorization_endpoint = https://test/oauth2/authorize/
token_endpoint = https://test/oauth2/token/
client_id = client-id
client_secret = client-secret
scope = profile
rememberer_name = fake

[plugin:fake]
use = ckanext.oauth2.tests.utils:FakeRememberer

[identifiers]
plugins = oauth2 fake

[authenticators]
plugins = oauth2

[challengers]
plugins = oauth2

[general]
challenge_decider = repoze.who.classifiers:default_challenge_decider
request_classifier = repoze.who.classifiers:default_request_classifier
'''


CHALLENGE_BODY = "CHALLENGE HO!"


class OAuth2PluginTest(unittest.TestCase):

    def _wsgi_app(self):
        parser = WhoConfig("")
        parser.parse(WHO_CONFIG)

        def application(environ, start_response):
            start_response("401 Unauthorized", [])
            return [""]

        return PluggableAuthenticationMiddleware(application,
                                 parser.identifiers,
                                 parser.authenticators,
                                 parser.challengers,
                                 parser.mdproviders,
                                 parser.request_classifier,
                                 parser.challenge_decider)

    def _plugin(self):
        return OAuth2Plugin(
            authorization_endpoint='https://test/oauth2/authorize/',
            token_endpoint='https://test/oauth2/token/',
            client_id='client-id',
            client_secret='client-secret',
            profile_api_user_field='nickName'
        )

    def test_implements(self):
        verifyClass(IIdentifier, OAuth2Plugin)
        verifyClass(IAuthenticator, OAuth2Plugin)
        verifyClass(IChallenger, OAuth2Plugin)

    def test_make_plugin_all(self):
        plugin = make_plugin(
            authorization_endpoint='https://test/oauth2/authorize/',
            token_endpoint='https://test/oauth2/token/',
            client_id='client-id',
            client_secret='client-secret',
            scope='profile other',
            rememberer_name='fake',
            profile_api_user_field='nickName')
        self.assertEquals(plugin.authorization_endpoint, 'https://test/oauth2/authorize/')
        self.assertEquals(plugin.token_endpoint, 'https://test/oauth2/token/')
        self.assertEquals(plugin.client_id, 'client-id')
        self.assertEquals(plugin.client_secret, 'client-secret')
        self.assertEquals(plugin.scope, ['profile', 'other'])
        self.assertEquals(plugin.rememberer_name, 'fake')
        self.assertEquals(plugin.profile_api_user_field, 'nickName')

    def test_make_plugin_missing(self):
        with self.assertRaises(ValueError):
            make_plugin()

    def test_identify_with_no_credentials(self):
        plugin = self._plugin()
        environ = make_environ()
        identity = plugin.identify(environ)
        self.assertEquals(identity, None)

    @httpretty.activate
    def test_identify(self):
        plugin = self._plugin()
        token = {
            'access_token': 'token',
            'token_type': 'Bearer',
            'expires_in': '3600',
            'refresh_token': 'refresh-token',
        }
        httpretty.register_uri(httpretty.POST, plugin.token_endpoint, body=json.dumps(token))
   
        state = b64encode(json.dumps({'came_from': 'initial-page'}))
        environ = make_environ(PATH_INFO=plugin.redirect_url, QUERY_STRING='state={0}&code=code'.format(state))
        identity = plugin.identify(environ)
        self.assertIn('oauth2.token', identity)

        for key in token:
            self.assertIn(key, identity['oauth2.token'])
            self.assertEquals(token[key], identity['oauth2.token'][key])

        self.assertIn('came_from', identity)
        self.assertEquals(identity['came_from'], 'initial-page')

    @httpretty.activate
    def test_identify_insecure(self):
        plugin = self._plugin()
        token = {
            'access_token': 'token',
            'token_type': 'Bearer',
            'expires_in': '3600',
            'refresh_token': 'refresh-token',
        }
        httpretty.register_uri(httpretty.POST, plugin.token_endpoint, body=json.dumps(token))

        state = b64encode(json.dumps({'came_from': 'initial-page'}))
        environ = make_environ(False, PATH_INFO=plugin.redirect_url, QUERY_STRING='state={0}&code=code'.format(state))
        with self.assertRaises(InsecureTransportError):
            plugin.identify(environ)

    # def test_remember(self):
    #     pass

    # def test_forget(self):
    #     pass

    # def test_challenge(self):
    #     pass
