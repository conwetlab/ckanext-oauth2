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
from urllib import urlencode
from repoze.who.interfaces import IIdentifier, IAuthenticator, IChallenger
from zope.interface.verify import verifyClass

OAUTH2TOKEN = {
    'access_token': 'token',
    'token_type': 'Bearer',
    'expires_in': '3600',
    'refresh_token': 'refresh_token',
}


class OAuth2PluginTest(unittest.TestCase):

    def setUp(self):

        self._user_field = 'nickName'
        self._fullname_field = 'fullname'
        self._email_field = 'mail'
        self._profile_api_url = 'https://test/oauth2/user'

        # Get the functions that can be mocked and affect other tests
        self._request = oauth2_repozewho.Request
        self._response = oauth2_repozewho.Response
        self._User = oauth2_repozewho.model.User
        self._Session = oauth2_repozewho.model.Session
        self._db = oauth2_repozewho.db
        self._OAuth2Session = oauth2_repozewho.OAuth2Session

    def tearDown(self):
        # Reset the functions
        oauth2_repozewho.Request = self._request
        oauth2_repozewho.Response = self._response
        oauth2_repozewho.model.User = self._User
        oauth2_repozewho.model.Session = self._Session
        oauth2_repozewho.db = self._db
        oauth2_repozewho.OAuth2Session = self._OAuth2Session

    def _plugin(self, fullname_field=True, mail_field=True):
        plugin = OAuth2Plugin(
            authorization_endpoint='https://test/oauth2/authorize/',
            token_endpoint='https://test/oauth2/token/',
            client_id='client-id',
            client_secret='client-secret',
            profile_api_url=self._profile_api_url,
            profile_api_user_field=self._user_field
        )

        if fullname_field:
            plugin.profile_api_fullname_field = self._fullname_field

        if mail_field:
            plugin.profile_api_mail_field = self._email_field

        return plugin

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
        token = OAUTH2TOKEN
        httpretty.register_uri(httpretty.POST, plugin.token_endpoint, body=json.dumps(token))

        state = b64encode(json.dumps({'came_from': 'initial-page'}))
        environ = make_environ(PATH_INFO=oauth2_repozewho.REDIRECT_URL, QUERY_STRING='state={0}&code=code'.format(state))
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
        token = OAUTH2TOKEN
        httpretty.register_uri(httpretty.POST, plugin.token_endpoint, body=json.dumps(token))

        state = b64encode(json.dumps({'came_from': 'initial-page'}))
        environ = make_environ(False, PATH_INFO=oauth2_repozewho.REDIRECT_URL, QUERY_STRING='state={0}&code=code'.format(state))
        result = plugin.identify(environ)
        self.assertEquals(None, result)

    @httpretty.activate
    def test_identify_error(self):
        plugin = self._plugin()
        token = {
            'error': 'auth_error',
            'error_description': 'Some description'
        }
        httpretty.register_uri(httpretty.POST, plugin.token_endpoint, body=json.dumps(token))

        state = b64encode(json.dumps({'came_from': 'initial-page'}))
        environ = make_environ(False, PATH_INFO=oauth2_repozewho.REDIRECT_URL, QUERY_STRING='state={0}&code=code'.format(state))
        result = plugin.identify(environ)
        self.assertEquals(None, result)

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
        ('/user/login', True, '/'),
        ('/user/login', True, '/about', '/about'),
        ('/user/login', True, 'http://google.es'),
        ('/user/login', True, 'http://localhost/'),
        ('/user/login', True, 'http://localhost/about', 'http://localhost/about'),
        ('/user/login', True, 'http://localhost/user/logged_out_redirect'),
        ('/user/login', True, '/user/logged_out_redirect'),
        ('/user/login', False),
        ('/ckan-admin', True, '/', '/dashboard', '/'),
        ('/ckan-admin', False, '/', '/dashboard', '/'),
        ('/ckan-admin', False, '/ckan-admin', '/dashboard', '/'),
        ('/ckan-admin', True, 'http://google.es/', '/', '/')
    ])
    def test_challenge(self, path, include_referer=True, referer='/', expected_referer='/dashboard', expected_url=None):

        # Create the plugin
        plugin = self._plugin()

        # Build mocks
        request = MagicMock()
        request.host = 'localhost'
        request.host_url = 'http://' + request.host
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
        state = urlencode({'state': b64encode(bytes(json.dumps({'came_from': expected_referer})))})
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
        ('test_user', 'Test User Full Name', 'test@test.com', True, True, True, '/about'),
        ('test_user', None, 'test@test.com', True, True, True, '/about'),
        ('test_user', 'Test User Full Name', None, True, True, True, '/about'),
        ('test_user', 'Test User Full Name', 'test@test.com', True, True, True, None),
        ('test_user', 'Test User Full Name', 'test@test.com', True, False, True, '/'),
        ('test_user', None, 'test@test.com', True, False, True, '/'),
        ('test_user', 'Test User Full Name', 'test@test.com', True, True, False, '/'),
        ('test_user', 'Test User Full Name', None, True, True, False, '/'),
        ('test_user', 'Test User Full Name', 'test@test.com', True, False, False, None),
        ('test_user', None, None, True, False, False, '/about')
    ])
    @httpretty.activate
    def test_authenticate(self, username, fullname=None, email=None, user_exists=True,
                          fullname_field=True, email_field=True, came_from='/'):

        plugin = self._plugin(fullname_field, email_field)
        plugin.update_token = MagicMock()   # Mock the function. It'll be tested separately

        # Simulate the HTTP Request
        user_info = {}
        user_info[self._user_field] = username

        if fullname:
            user_info[self._fullname_field] = fullname

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
        oauth2_repozewho.model.Session = MagicMock()
        user = MagicMock()
        user.name = username
        user.fullname = None
        user.email = None
        oauth2_repozewho.model.User = MagicMock(return_value=user)
        oauth2_repozewho.model.User.by_name = MagicMock(return_value=user if user_exists else None)

        identity = {}
        identity['oauth2.token'] = OAUTH2TOKEN

        if came_from is not None:
            identity['came_from'] = came_from
            expected_came_from = came_from
        else:
            expected_came_from = '/dashboard'

        # Call the function
        plugin.authenticate(environ, identity)

        # Asserts
        oauth2_repozewho.Request.assert_called_once_with(environ)
        oauth2_repozewho.model.User.by_name.assert_called_once_with(username)

        # Check if the user is created or not
        if not user_exists:
            oauth2_repozewho.model.User.assert_called_once_with(name=username)
        else:
            self.assertEquals(0, oauth2_repozewho.model.User.called)

        # Check that user properties are set properly
        if fullname and fullname_field:
            self.assertEquals(fullname, user.fullname)
        else:
            self.assertEquals(None, user.fullname)

        if email and email_field:
            self.assertEquals(email, user.email)
        else:
            self.assertEquals(None, user.email)

        # Check that the user is saved
        plugin.update_token.assert_called_once_with(username, OAUTH2TOKEN)
        oauth2_repozewho.model.Session.add.assert_called_once_with(user)
        oauth2_repozewho.model.Session.commit.assert_called_once()
        oauth2_repozewho.model.Session.remove.assert_called_once()

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

    def test_authenticate_no_token(self):

        plugin = self._plugin()
        environ = identity = {}

        result = plugin.authenticate(environ, identity)

        self.assertEquals(None, result)

    def test_get_token_non_existing_user(self):
        plugin = self._plugin()
        oauth2_repozewho.db.UserToken.by_user_name = MagicMock(return_value=None)
        self.assertIsNone(plugin.get_token('user'))

    def test_get_token_existing_user(self):
        plugin = self._plugin()

        usertoken = MagicMock()
        usertoken.access_token = OAUTH2TOKEN['access_token']
        usertoken.token_type = OAUTH2TOKEN['token_type']
        usertoken.expires_in = OAUTH2TOKEN['expires_in']
        usertoken.refresh_token = OAUTH2TOKEN['refresh_token']

        oauth2_repozewho.db.UserToken.by_user_name = MagicMock(return_value=usertoken)
        self.assertEquals(OAUTH2TOKEN, plugin.get_token('user'))

    @parameterized.expand([
        (True,),
        (False,)
    ])
    def test_update_token(self, user_exists):
        plugin = self._plugin()

        if user_exists:
            usertoken = MagicMock()
            usertoken.access_token = OAUTH2TOKEN['access_token']
            usertoken.token_type = OAUTH2TOKEN['token_type']
            usertoken.expires_in = OAUTH2TOKEN['expires_in']
            usertoken.refresh_token = OAUTH2TOKEN['refresh_token']
        else:
            usertoken = None
            oauth2_repozewho.db.UserToken = MagicMock()

        oauth2_repozewho.model.Session = MagicMock()
        oauth2_repozewho.db.UserToken.by_user_name = MagicMock(return_value=usertoken)

        # The token to be updated
        newtoken = {
            'access_token': 'new_access_token',
            'token_type': 'new_token_type',
            'expires_in': 'new_expires_in',
            'refresh_token': 'new_refresh_token'
        }

        plugin.update_token('user', newtoken)

        # Check that the object has been stored
        oauth2_repozewho.model.Session.add.assert_called_once()
        oauth2_repozewho.model.Session.commit.assert_called_once()

        # Check that the object contains the correct information
        tk = oauth2_repozewho.model.Session.add.call_args_list[0][0][0]
        self.assertEquals(newtoken['access_token'], tk.access_token)
        self.assertEquals(newtoken['token_type'], tk.token_type)
        self.assertEquals(newtoken['expires_in'], tk.expires_in)
        self.assertEquals(newtoken['refresh_token'], tk.refresh_token)

    @parameterized.expand([
        (True,),
        (False,)
    ])
    def test_refresh_token(self, user_exists):
        username = 'user'
        plugin = self._plugin()

        # mock get_token
        if user_exists:
            current_token = OAUTH2TOKEN
        else:
            current_token = None

        plugin.get_token = MagicMock(return_value=current_token)

        # mock update_token
        plugin.update_token = MagicMock()

        # The token returned by the system
        newtoken = {
            'access_token': 'new_access_token',
            'token_type': 'new_token_type',
            'expires_in': 'new_expires_in',
            'refresh_token': 'new_refresh_token'
        }
        session = MagicMock()
        session.refresh_token = MagicMock(return_value=newtoken)
        oauth2_repozewho.OAuth2Session = MagicMock(return_value=session)

        # Call the function
        plugin.refresh_token(username)

        if user_exists:
            oauth2_repozewho.OAuth2Session.assert_called_once_with(plugin.client_id, token=current_token, scope=plugin.scope)
            session.refresh_token.assert_called_once_with(plugin.token_endpoint, client_secret=plugin.client_secret, client_id=plugin.client_id)
            plugin.update_token.assert_called_once_with(username, newtoken)
        else:
            self.assertEquals(0, oauth2_repozewho.OAuth2Session.call_count)
            self.assertEquals(0, session.refresh_token.call_count)
            self.assertEquals(0, plugin.update_token.call_count)
