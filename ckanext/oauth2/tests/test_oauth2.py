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

import unittest
import json

import httpretty
import ckanext.oauth2.oauth2 as oauth2

from base64 import b64encode
from ckanext.oauth2.oauth2 import OAuth2Helper
from mock import MagicMock
from nose_parameterized import parameterized
from oauthlib.oauth2 import InsecureTransportError, MissingCodeError, MissingTokenError
from urllib import urlencode

OAUTH2TOKEN = {
    'access_token': 'token',
    'token_type': 'Bearer',
    'expires_in': '3600',
    'refresh_token': 'refresh_token',
}


def make_request(secure, host, path, params):
    request = MagicMock()

    # Generate the string of paramaters1
    params_str = ''
    for param in params:
        params_str += '%s=%s&' % (param, params[param])

    secure = 's' if secure else ''
    request.url = 'http%s://%s/%s?%s' % (secure, host, path, params_str)
    request.host = host
    request.host_url = 'http%s://%s' % (secure, host)
    request.params = params
    return request


class OAuth2PluginTest(unittest.TestCase):

    def setUp(self):

        self._user_field = 'nickName'
        self._fullname_field = 'fullname'
        self._email_field = 'mail'
        self._profile_api_url = 'https://test/oauth2/user'

        # Get the functions that can be mocked and affect other tests
        self._toolkit = oauth2.toolkit
        self._User = oauth2.model.User
        self._Session = oauth2.model.Session
        self._db = oauth2.db
        self._OAuth2Session = oauth2.OAuth2Session

    def tearDown(self):
        # Reset the functions
        oauth2.toolkit = self._toolkit
        oauth2.model.User = self._User
        oauth2.model.Session = self._Session
        oauth2.db = self._db
        oauth2.OAuth2Session = self._OAuth2Session

        # Recover the function since it'll be mocked in a test...
        if getattr(self, 'plugin', None) is not None and getattr(self, '_update_token', None) is not None:
            self.plugin.update_token = self._update_token

        if getattr(self, 'plugin', None) is not None and getattr(self, '_get_token', None) is not None:
            self.plugin.get_token = self._get_token

    def _helper(self, fullname_field=True, mail_field=True):
        oauth2.db = MagicMock()

        oauth2.config = {
            'ckan.oauth2.authorization_endpoint': 'https://test/oauth2/authorize/',
            'ckan.oauth2.token_endpoint': 'https://test/oauth2/token/',
            'ckan.oauth2.client_id': 'client-id',
            'ckan.oauth2.client_secret': 'client-secret',
            'ckan.oauth2.profile_api_url': self._profile_api_url,
            'ckan.oauth2.profile_api_user_field': self._user_field
        }

        helper = OAuth2Helper()

        if fullname_field:
            helper.profile_api_fullname_field = self._fullname_field

        if mail_field:
            helper.profile_api_mail_field = self._email_field

        return helper

    def test_get_token_with_no_credentials(self):
        oauth2.toolkit = MagicMock()
        state = b64encode(json.dumps({'came_from': 'initial-page'}))
        oauth2.toolkit.request = make_request(True, 'data.com', 'callback', {'state': state})

        helper = self._helper()

        with self.assertRaises(MissingCodeError):
            helper.get_token()

    @httpretty.activate
    def test_get_token(self):
        oauth2.toolkit = MagicMock()
        helper = self._helper()
        token = OAUTH2TOKEN
        httpretty.register_uri(httpretty.POST, helper.token_endpoint, body=json.dumps(token))

        state = b64encode(json.dumps({'came_from': 'initial-page'}))
        oauth2.toolkit.request = make_request(True, 'data.com', 'callback', {'state': state, 'code': 'code'})
        retrieved_token = helper.get_token()

        for key in token:
            self.assertIn(key, retrieved_token)
            self.assertEquals(token[key], retrieved_token[key])

    @httpretty.activate
    def test_get_token_insecure(self):
        oauth2.toolkit = MagicMock()
        helper = self._helper()
        token = OAUTH2TOKEN
        httpretty.register_uri(httpretty.POST, helper.token_endpoint, body=json.dumps(token))

        state = b64encode(json.dumps({'came_from': 'initial-page'}))
        oauth2.toolkit.request = make_request(False, 'data.com', 'callback', {'state': state, 'code': 'code'})

        with self.assertRaises(InsecureTransportError):
            helper.get_token()

    @httpretty.activate
    def test_get_token_error(self):
        oauth2.toolkit = MagicMock()
        helper = self._helper()
        token = {
            'error': 'auth_error',
            'error_description': 'Some description'
        }
        httpretty.register_uri(httpretty.POST, helper.token_endpoint, body=json.dumps(token))

        state = b64encode(json.dumps({'came_from': 'initial-page'}))
        oauth2.toolkit.request = make_request(True, 'data.com', 'callback', {'state': state, 'code': 'code'})

        with self.assertRaises(MissingTokenError):
            helper.get_token()

    @parameterized.expand([
        ({},),
        ([('Set-Cookie', 'cookie1="cookie1val"; Path=/')],),
        ([('Set-Cookie', 'cookie1="cookie1val"; Path=/'), ('Set-Cookie', 'cookie12="cookie2val"; Path=/')],)
    ])
    def test_remember(self, headers):
        user_name = 'user_name'

        # Configure the mocks
        oauth2.toolkit = MagicMock()
        environ = MagicMock()
        plugins = MagicMock()
        authenticator = MagicMock()
        authenticator.remember = MagicMock(return_value=headers)

        environ.get = MagicMock(return_value=plugins)
        oauth2.toolkit.request.environ = environ
        plugins.get = MagicMock(return_value=authenticator)

        # Call the function
        helper = self._helper()
        helper.remember(user_name)

        # Check that the remember method has been called properly
        authenticator.remember.assert_called_once_with(environ, {'repoze.who.userid': user_name})

        for header, value in headers:
            oauth2.toolkit.response.headers.add.assert_any_call(header, value)

    def test_challenge(self):
        helper = self._helper()

        # Build mocks
        request = MagicMock()
        request = make_request(False, 'localhost', 'user/login', {})
        request.environ = MagicMock()
        request.headers = {}
        came_from = '/came_from_example'

        oauth2.toolkit = MagicMock()
        oauth2.toolkit.request = request
        oauth2.toolkit.response = MagicMock()

        # Call the method
        helper.challenge(came_from)

        # Check
        state = urlencode({'state': b64encode(bytes(json.dumps({'came_from': came_from})))})
        expected_url = 'https://test/oauth2/authorize/?response_type=code&client_id=client-id&' + \
                       'redirect_uri=http%3A%2F%2Flocalhost%2Foauth2%2Fcallback&' + state
        self.assertEquals(302, oauth2.toolkit.response.status)
        self.assertEquals(expected_url, oauth2.toolkit.response.location)

    @parameterized.expand([
        ('test_user', 'Test User Full Name', 'test@test.com'),
        ('test_user', None, 'test@test.com'),
        ('test_user', 'Test User Full Name', None),
        ('test_user', 'Test User Full Name', 'test@test.com', False),
        ('test_user', None, 'test@test.com', False),
        ('test_user', 'Test User Full Name', None, False),
        ('test_user', 'Test User Full Name', 'test@test.com', True, True, True),
        ('test_user', None, 'test@test.com', True, True, True),
        ('test_user', 'Test User Full Name', None, True, True, True),
        ('test_user', 'Test User Full Name', 'test@test.com', True, True, True),
        ('test_user', 'Test User Full Name', 'test@test.com', True, False, True),
        ('test_user', None, 'test@test.com', True, False, True),
        ('test_user', 'Test User Full Name', 'test@test.com', True, True, False),
        ('test_user', 'Test User Full Name', None, True, True, False),
        ('test_user', 'Test User Full Name', 'test@test.com', True, False, False),
        ('test_user', None, None, True, False, False)
    ])
    @httpretty.activate
    def test_identify(self, username, fullname=None, email=None, user_exists=True,
                      fullname_field=True, email_field=True):

        self.helper = helper = self._helper(fullname_field, email_field)

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
        request = make_request(False, 'localhost', '/oauth2/callback', {})
        oauth2.toolkit = MagicMock()
        oauth2.toolkit.request = request
        oauth2.model.Session = MagicMock()
        user = MagicMock()
        user.name = username
        user.fullname = None
        user.email = None
        oauth2.model.User = MagicMock(return_value=user)
        oauth2.model.User.by_name = MagicMock(return_value=user if user_exists else None)

        # Call the function
        returned_username = helper.identify(OAUTH2TOKEN)

        # The function must return the user name
        self.assertEquals(username, returned_username)

        # Asserts
        oauth2.model.User.by_name.assert_called_once_with(username)

        # Check if the user is created or not
        if not user_exists:
            oauth2.model.User.assert_called_once_with(name=username)
        else:
            self.assertEquals(0, oauth2.model.User.called)

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
        oauth2.model.Session.add.assert_called_once_with(user)
        oauth2.model.Session.commit.assert_called_once()
        oauth2.model.Session.remove.assert_called_once()

    @parameterized.expand([
        ({'error': 'invalid_token', 'error_description': 'Error Description'},),
        ({'error': 'another_error'},)
    ])
    @httpretty.activate
    def test_identify_invalid_token(self, user_info):

        helper = self._helper()
        token = {'access_token': 'OAUTH_TOKEN'}

        httpretty.register_uri(httpretty.GET, helper.profile_api_url, status=401, body=json.dumps(user_info))

        exception_risen = False
        try:
            helper.identify(token)
        except Exception as e:
            if user_info['error'] == 'invalid_token':
                self.assertIsInstance(e, ValueError)
                self.assertEquals(user_info['error_description'], e.message)
            exception_risen = True

        self.assertTrue(exception_risen)

    def test_get_stored_token_non_existing_user(self):
        helper = self._helper()
        oauth2.db.UserToken.by_user_name = MagicMock(return_value=None)
        self.assertIsNone(helper.get_stored_token('user'))

    def test_get_stored_token_existing_user(self):
        helper = self._helper()

        usertoken = MagicMock()
        usertoken.access_token = OAUTH2TOKEN['access_token']
        usertoken.token_type = OAUTH2TOKEN['token_type']
        usertoken.expires_in = OAUTH2TOKEN['expires_in']
        usertoken.refresh_token = OAUTH2TOKEN['refresh_token']

        oauth2.db.UserToken.by_user_name = MagicMock(return_value=usertoken)
        self.assertEquals(OAUTH2TOKEN, helper.get_stored_token('user'))

    @parameterized.expand([
        ({'came_from': 'http://localhost/dataset'}, ),
        ({},)
    ])
    def test_redirect_from_callback(self, identity):
        oauth2.toolkit = MagicMock()
        came_from = 'initial-page'
        state = b64encode(json.dumps({'came_from': came_from}))
        oauth2.toolkit.request = make_request(True, 'data.com', 'callback', {'state': state, 'code': 'code'})

        helper = self._helper()
        helper.redirect_from_callback()

        self.assertEquals(302, oauth2.toolkit.response.status)
        self.assertEquals(came_from, oauth2.toolkit.response.location)

    @parameterized.expand([
        (True,),
        (False,)
    ])
    def test_update_token(self, user_exists):
        helper = self._helper()
        user = 'user'

        if user_exists:
            usertoken = MagicMock()
            usertoken.user_name = user
            usertoken.access_token = OAUTH2TOKEN['access_token']
            usertoken.token_type = OAUTH2TOKEN['token_type']
            usertoken.expires_in = OAUTH2TOKEN['expires_in']
            usertoken.refresh_token = OAUTH2TOKEN['refresh_token']
        else:
            usertoken = None
            oauth2.db.UserToken = MagicMock()

        oauth2.model.Session = MagicMock()
        oauth2.db.UserToken.by_user_name = MagicMock(return_value=usertoken)

        # The token to be updated
        newtoken = {
            'access_token': 'new_access_token',
            'token_type': 'new_token_type',
            'expires_in': 'new_expires_in',
            'refresh_token': 'new_refresh_token'
        }

        helper.update_token('user', newtoken)

        # Check that the object has been stored
        oauth2.model.Session.add.assert_called_once()
        oauth2.model.Session.commit.assert_called_once()

        # Check that the object contains the correct information
        tk = oauth2.model.Session.add.call_args_list[0][0][0]
        self.assertEquals(user, tk.user_name)
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
        helper = self.helper = self._helper()

        # mock get_token
        if user_exists:
            current_token = OAUTH2TOKEN
        else:
            current_token = None

        # save functions that will be mocked (they'll be recovered in tearDown)
        self._get_token = self.helper.get_token
        self._update_token = self.helper.update_token

        # mock plugin functions
        helper.get_stored_token = MagicMock(return_value=current_token)
        helper.update_token = MagicMock()

        # The token returned by the system
        newtoken = {
            'access_token': 'new_access_token',
            'token_type': 'new_token_type',
            'expires_in': 'new_expires_in',
            'refresh_token': 'new_refresh_token'
        }
        session = MagicMock()
        session.refresh_token = MagicMock(return_value=newtoken)
        oauth2.OAuth2Session = MagicMock(return_value=session)

        # Call the function
        result = helper.refresh_token(username)

        if user_exists:
            self.assertEquals(newtoken, result)
            helper.get_stored_token.assert_called_once_with(username)
            oauth2.OAuth2Session.assert_called_once_with(helper.client_id, token=current_token, scope=helper.scope)
            session.refresh_token.assert_called_once_with(helper.token_endpoint, client_secret=helper.client_secret, client_id=helper.client_id)
            helper.update_token.assert_called_once_with(username, newtoken)
        else:
            self.assertIsNone(result)
            self.assertEquals(0, oauth2.OAuth2Session.call_count)
            self.assertEquals(0, session.refresh_token.call_count)
            self.assertEquals(0, helper.update_token.call_count)
