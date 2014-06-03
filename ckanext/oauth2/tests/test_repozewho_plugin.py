# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
import json

import httpretty
import ckanext.oauth2.repozewho as oauth2_repozewho

from base64 import b64encode
from ckanext.oauth2.repozewho import OAuth2Plugin, make_plugin
from ckanext.oauth2.tests.utils import make_environ
from mock import MagicMock
from nose_parameterized import parameterized
from oauthlib.oauth2 import InsecureTransportError
from urllib import urlencode
from repoze.who.interfaces import IIdentifier, IAuthenticator, IChallenger
from zope.interface.verify import verifyClass


class OAuth2PluginTest(unittest.TestCase):

    def setUp(self):

        self._user_field = 'nickName'
        self._fullname_field = 'fullname'
        self._email_field = 'mail'
        self._profile_api_url = 'https://test/oauth2/user'

        # Get the functions that can be mocked and affect other tests
        self._request = oauth2_repozewho.Request
        self._response = oauth2_repozewho.Response
        self._User = oauth2_repozewho.User
        self._Session = oauth2_repozewho.Session

    def tearDown(self):
        # Reset the functions
        oauth2_repozewho.Request = self._request
        oauth2_repozewho.Response = self._response
        oauth2_repozewho.User = self._User
        oauth2_repozewho.Session = self._Session

    def _plugin(self):
        return OAuth2Plugin(
            authorization_endpoint='https://test/oauth2/authorize/',
            token_endpoint='https://test/oauth2/token/',
            client_id='client-id',
            client_secret='client-secret',
            profile_api_url=self._profile_api_url,
            profile_api_user_field=self._user_field,
            profile_api_fullname_field=self._fullname_field,
            profile_api_mail_field=self._email_field
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
            profile_api_url='https://test/oauth2/user',
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

    @parameterized.expand([
        ('remember'),
        ('forget')
    ])
    def test_remember_forget(self, function_name):

        # Configure the mocks
        environ = MagicMock()
        authenticator = MagicMock()
        plugins = MagicMock()
        plugins.get = MagicMock(return_value=authenticator)
        environ.get = MagicMock(return_value=plugins)

        identity = MagicMock()

        # Call the function
        plugin = self._plugin()
        getattr(plugin, function_name)(environ, identity)

        # Check that the remember method has been called properly
        getattr(authenticator, function_name).assert_called_once_with(environ, identity)

    @parameterized.expand([
        ('/user/login', '/'),
        ('/user/login', '/about'),
        ('/user/login', False),
        ('/ckan-admin', True, '/', '/'),
        ('/ckan-admin', False, '/', '/')
    ])
    def test_challenge(self, path, include_referer=True, referer='/', expected_url=None):

        # Create the plugin
        plugin = self._plugin()

        # Build mocks
        request = MagicMock()
        request.host_url = 'http://localhost'
        request.path = path
        request.headers = {}
        if include_referer:
            request.headers['Referer'] = referer
        oauth2_repozewho.Request = MagicMock(return_value=request)
        oauth2_repozewho.Response = MagicMock()
        environ = MagicMock()

        # Call the method
        response = plugin.challenge(environ, 0)

        # Check
        state = urlencode({'state': b64encode(bytes(json.dumps({'came_from': referer})))})
        callback_url = 'https://test/oauth2/authorize/?response_type=code&client_id=client-id&' + \
                       'redirect_uri=http%3A%2F%2Flocalhost%2Foauth2%2Fcallback&' + state
        expected_url = expected_url if expected_url is not None else callback_url
        oauth2_repozewho.Request.assert_called_once_with(environ)
        self.assertEquals(302, response.status)
        self.assertEquals(expected_url, response.location)

    @parameterized.expand([
        ('test_user', 'Test User Full Name', 'test@test.com'),
        ('test_user', None, 'test@test.com'),
        ('test_user', 'Test User Full Name', None),
        ('test_user', 'Test User Full Name', 'test@test.com', False),
        ('test_user', None, 'test@test.com', False),
        ('test_user', 'Test User Full Name', None, False),
        ('test_user', 'Test User Full Name', 'test@test.com', True, '/about'),
        ('test_user', None, 'test@test.com', True, '/about'),
        ('test_user', 'Test User Full Name', None, True, '/about'),
        ('test_user', 'Test User Full Name', 'test@test.com', True, None)
    ])
    @httpretty.activate
    def test_authenticate(self, username, full_name=None, email=None, user_exists=True, came_from='/'):

        plugin = self._plugin()

        # Simulate the HTTP Request
        user_info = {}
        user_info[self._user_field] = username

        if full_name:
            user_info[self._fullname_field] = full_name

        if email:
            user_info[self._email_field] = email

        httpretty.register_uri(httpretty.GET, self._profile_api_url, body=json.dumps(user_info))

        # Create the mocks
        request = MagicMock()
        request.host_url = 'http://localhost'
        request.path = '/oauth2/callback'
        request.environ = {}    # It's used inside the function. Needed to get the response
        oauth2_repozewho.Request = MagicMock(return_value=request)
        oauth2_repozewho.Response = MagicMock()
        environ = MagicMock()
        oauth2_repozewho.Session = MagicMock()
        user = MagicMock()
        user.name = username
        oauth2_repozewho.User = MagicMock(return_value=user)
        oauth2_repozewho.User.by_name = MagicMock(return_value=user if user_exists else None)

        identity = {}
        identity['oauth2.token'] = {
            'access_token': 'OAUTH_TOKEN',
            'token_type': 'bearer',
            'expires_in': 2591999,
            'expires_at': 9904315459.21328,
            'refresh_token': 'REFRESH_TOKEN'
        }

        if came_from is not None:
            identity['came_from'] = came_from
            expected_came_from = came_from
        else:
            expected_came_from = '/'

        # Call the function
        plugin.authenticate(environ, identity)

        # Asserts
        oauth2_repozewho.Request.assert_called_once_with(environ)
        oauth2_repozewho.User.by_name.assert_called_once_with(username)

        # Check if the user is created or not
        if not user_exists:
            oauth2_repozewho.User.assert_called_once_with(name=username)
        else:
            self.assertEquals(0, oauth2_repozewho.User.called)

        # Check that user properties are set properly
        if full_name:
            self.assertEquals(full_name, user.fullname)

        if email:
            self.assertEquals(email, user.email)

        # Check that the user is saved
        oauth2_repozewho.Session.add.assert_called_once_with(user)
        oauth2_repozewho.Session.commit.assert_called_once()
        oauth2_repozewho.Session.remove.assert_called_once()

        # The identity object should contain the user name
        self.assertIn('repoze.who.userid', identity)
        self.assertEquals(username, identity['repoze.who.userid'])

        # Get the response
        self.assertIn('repoze.who.application', request.environ)
        response = request.environ['repoze.who.application']
        self.assertEquals(302, response.status)
        self.assertEquals(expected_came_from, response.location)

    @httpretty.activate
    def test_authenticate_invalid_token(self):

        plugin = self._plugin()
        user_info = {}
        environ = {}
        identity = {}
        identity['oauth2.token'] = 'OAUTH_TOKEN'

        httpretty.register_uri(httpretty.GET, self._profile_api_url, body=json.dumps(user_info))

        with self.assertRaises(ValueError):
            plugin.authenticate(environ, identity)
