# -*- coding: utf-8 -*-

# Copyright (c) 2014 CoNWeT Lab., Universidad Politécnica de Madrid
# Copyright (c) 2018 Future Internet Consulting and Development Solutions S.L.

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

from base64 import b64encode, urlsafe_b64encode
import json
import os
import unittest
from urllib.parse import urlencode

import ckanext.oauth2.oauth2 as oauth2
from ckanext.oauth2.oauth2 import OAuth2Helper
import httpretty
from unittest.mock import patch, MagicMock
from parameterized import parameterized
from oauthlib.oauth2 import InsecureTransportError, MissingCodeError, MissingTokenError
from requests.exceptions import SSLError

OAUTH2TOKEN = {
    'access_token': 'token',
    'token_type': 'Bearer',
    'expires_in': '3600',
    'refresh_token': 'refresh_token',
}


def make_request(secure, host, path, params):
    request = MagicMock()

    params_str = ''
    for param in params:
        params_str += '%s=%s&' % (param, params[param])

    secure = 's' if secure else ''
    request.url = 'http%s://%s/%s?%s' % (secure, host, path, params_str)
    request.host = host
    request.host_url = 'http%s://%s' % (secure, host)
    request.args = params
    return request


class OAuth2PluginTest(unittest.TestCase):

    def setUp(self):

        self._user_field = 'nickName'
        self._fullname_field = 'fullname'
        self._email_field = 'mail'
        self._profile_api_url = 'https://test/oauth2/user'
        self._group_field = 'groups'

        self._toolkit = oauth2.toolkit
        self._User = oauth2.model.User
        self._Session = oauth2.model.Session
        self._db = oauth2.db
        self._OAuth2Session = oauth2.OAuth2Session

        oauth2.toolkit = MagicMock()

    def tearDown(self):
        oauth2.toolkit = self._toolkit
        oauth2.model.User = self._User
        oauth2.model.Session = self._Session
        oauth2.db = self._db
        oauth2.OAuth2Session = self._OAuth2Session

    def _helper(self, fullname_field=True, mail_field=True, conf=None, missing_conf=None, jwt_enable=False):
        oauth2.db = MagicMock()
        oauth2.jwt = MagicMock()

        oauth2.toolkit.config = {
            'ckan.oauth2.legacy_idm': 'false',
            'ckan.oauth2.authorization_endpoint': 'https://test/oauth2/authorize/',
            'ckan.oauth2.token_endpoint': 'https://test/oauth2/token/',
            'ckan.oauth2.client_id': 'client-id',
            'ckan.oauth2.client_secret': 'client-secret',
            'ckan.oauth2.profile_api_url': self._profile_api_url,
            'ckan.oauth2.profile_api_user_field': self._user_field,
            'ckan.oauth2.profile_api_mail_field': self._email_field,
        }
        if conf is not None:
            oauth2.toolkit.config.update(conf)
        if missing_conf is not None:
            del oauth2.toolkit.config[missing_conf]

        helper = OAuth2Helper()

        if fullname_field:
            helper.profile_api_fullname_field = self._fullname_field

        if jwt_enable:
            helper.jwt_enable = True

        return helper

    @parameterized.expand([
        ("ckan.oauth2.authorization_endpoint"),
        ("ckan.oauth2.token_endpoint"),
        ("ckan.oauth2.client_id"),
        ("ckan.oauth2.client_secret"),
        ("ckan.oauth2.profile_api_url"),
        ("ckan.oauth2.profile_api_user_field"),
        ("ckan.oauth2.profile_api_mail_field"),
    ])
    def test_minimum_conf(self, conf_to_remove):
        with self.assertRaises(ValueError):
            self._helper(missing_conf=conf_to_remove)

    @patch('ckanext.oauth2.oauth2.OAuth2Session')
    def test_get_token_with_no_credentials(self, oauth2_session_mock):
        state = b64encode(json.dumps({'came_from': 'initial-page'}).encode('utf-8')).decode('utf-8')
        oauth2.toolkit.request = make_request(True, 'data.com', 'callback', {'state': state})

        helper = self._helper()

        oauth2_session_mock().fetch_token.side_effect = MissingCodeError("Missing code parameter in response.")
        with self.assertRaises(MissingCodeError):
            helper.get_token()

    @patch('ckanext.oauth2.oauth2.OAuth2Session')
    @patch.dict(os.environ, {'OAUTHLIB_INSECURE_TRANSPORT': ''})
    def test_get_token(self, OAuth2Session):
        helper = self._helper()
        token = OAUTH2TOKEN
        OAuth2Session().fetch_token.return_value = OAUTH2TOKEN

        state = b64encode(json.dumps({'came_from': 'initial-page'}).encode('utf-8')).decode('utf-8')
        oauth2.toolkit.request = make_request(True, 'data.com', 'callback', {'state': state, 'code': 'code'})
        retrieved_token = helper.get_token()

        for key in token:
            self.assertIn(key, retrieved_token)
            self.assertEqual(token[key], retrieved_token[key])

    @patch('ckanext.oauth2.oauth2.OAuth2Session')
    def test_get_token_legacy_idm(self, OAuth2Session):
        helper = self._helper()
        helper.legacy_idm = True
        helper.verify_https = True
        OAuth2Session().fetch_token.return_value = OAUTH2TOKEN

        state = b64encode(json.dumps({'came_from': 'initial-page'}).encode('utf-8')).decode('utf-8')
        oauth2.toolkit.request = make_request(True, 'data.com', 'callback', {'state': state, 'code': 'code'})
        retrieved_token = helper.get_token()

        expected_headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': 'Basic %s' % urlsafe_b64encode(
                ('%s:%s' % (helper.client_id, helper.client_secret)).encode('utf-8')
            ).decode('utf-8')
        }

        OAuth2Session().fetch_token.assert_called_once_with(
            helper.token_endpoint,
            headers=expected_headers,
            client_secret=helper.client_secret,
            authorization_response=oauth2.toolkit.request.url,
            verify=True
        )
        self.assertEqual(retrieved_token, OAUTH2TOKEN)

    @httpretty.activate
    @patch.dict(os.environ, {'OAUTHLIB_INSECURE_TRANSPORT': ''})
    def test_get_token_insecure(self):
        helper = self._helper()
        token = OAUTH2TOKEN
        httpretty.register_uri(httpretty.POST, helper.token_endpoint, body=json.dumps(token))

        state = b64encode(json.dumps({'came_from': 'initial-page'}).encode('utf-8')).decode('utf-8')
        oauth2.toolkit.request = make_request(False, 'data.com', 'callback', {'state': state, 'code': 'code'})

        with self.assertRaises(InsecureTransportError):
            helper.get_token()

    @httpretty.activate
    @patch.dict(os.environ, {'OAUTHLIB_INSECURE_TRANSPORT': ''})
    def test_get_token_invalid_cert(self):
        helper = self._helper()
        token = OAUTH2TOKEN
        httpretty.register_uri(httpretty.POST, helper.token_endpoint, body=json.dumps(token))

        state = b64encode(json.dumps({'came_from': 'initial-page'}).encode('utf-8')).decode('utf-8')
        oauth2.toolkit.request = make_request(True, 'data.com', 'callback', {'state': state, 'code': 'code'})

        with self.assertRaises(InsecureTransportError):
            with patch('ckanext.oauth2.oauth2.OAuth2Session') as oauth2_session_mock:
                oauth2_session_mock().fetch_token.side_effect = SSLError('(Caused by SSLError(SSLError("bad handshake: Error([(\'SSL routines\', \'tls_process_server_certificate\', \'certificate verify failed\')],)",),)')
                helper.get_token()

    @httpretty.activate
    @patch.dict(os.environ, {'OAUTHLIB_INSECURE_TRANSPORT': ''})
    def test_get_token_unexpected_ssl_error(self):
        helper = self._helper()
        token = OAUTH2TOKEN
        httpretty.register_uri(httpretty.POST, helper.token_endpoint, body=json.dumps(token))

        state = b64encode(json.dumps({'came_from': 'initial-page'}).encode('utf-8')).decode('utf-8')
        oauth2.toolkit.request = make_request(True, 'data.com', 'callback', {'state': state, 'code': 'code'})

        with self.assertRaises(SSLError):
            with patch('ckanext.oauth2.oauth2.OAuth2Session') as oauth2_session_mock:
                oauth2_session_mock().fetch_token.side_effect = SSLError('unexpected error')
                helper.get_token()

    @httpretty.activate
    @patch.dict(os.environ, {'OAUTHLIB_INSECURE_TRANSPORT': 'True'})
    def test_get_token_insecure_enabled(self):
        helper = self._helper()
        token = OAUTH2TOKEN
        httpretty.register_uri(httpretty.POST, helper.token_endpoint, body=json.dumps(token))

        state = b64encode(json.dumps({'came_from': 'initial-page'}).encode('utf-8')).decode('utf-8')
        oauth2.toolkit.request = make_request(False, 'data.com', 'callback', {'state': state, 'code': 'code'})
        retrieved_token = helper.get_token()

        for key in token:
            self.assertIn(key, retrieved_token)
            self.assertEqual(token[key], retrieved_token[key])

    @httpretty.activate
    def test_get_token_error(self):
        helper = self._helper()
        token = {
            'info': 'auth_error',
            'error_description': 'Some description'
        }
        httpretty.register_uri(httpretty.POST, helper.token_endpoint, body=json.dumps(token))

        state = b64encode(json.dumps({'came_from': 'initial-page'}).encode('utf-8')).decode('utf-8')
        oauth2.toolkit.request = make_request(True, 'data.com', 'callback', {'state': state, 'code': 'code'})

        with self.assertRaises(MissingTokenError):
            helper.get_token()

    @parameterized.expand([
        ('test_user', 'Test User Full Name', 'test@test.com'),
        ('test_user', None,                  'test@test.com'),
        ('test_user', 'Test User Full Name', 'test@test.com', False),
        ('test_user', None,                  'test@test.com', False),
        ('test_user', None,                  'test@test.com', False, False, False),
        ('test_user', None,                  'test@test.com', False, False, True),
        ('test_user', 'Test User Full Name', 'test@test.com', True, True),
        ('test_user', 'Test User Full Name', 'test@test.com', True, False),
        ('test_user', 'Test User Full Name', 'test@test.com', True, True, True),
        ('test_user', 'Test User Full Name', 'test@test.com', True, True, False),
        ('test_user', None,                  'test@test.com', True, True),
        ('test_user', None,                  'test@test.com', True, False),
    ])
    @httpretty.activate
    def test_identify(self, username, fullname=None, email=None, user_exists=True,
                      fullname_field=True, sysadmin=None):

        self.helper = helper = self._helper(fullname_field)

        user_info = {}
        user_info[self._user_field] = username
        user_info[self._email_field] = email

        if fullname:
            user_info[self._fullname_field] = fullname

        if sysadmin is not None:
            self.helper.profile_api_groupmembership_field = self._group_field
            self.helper.sysadmin_group_name = "admin"
            user_info[self._group_field] = "admin" if sysadmin else "other"

        httpretty.register_uri(httpretty.GET, self._profile_api_url, body=json.dumps(user_info))

        request = make_request(False, 'localhost', '/oauth2/callback', {})
        oauth2.toolkit.request = request
        oauth2.model.Session = MagicMock()
        user = MagicMock()
        user.name = None
        user.fullname = None
        user.email = email
        oauth2.model.User = MagicMock(return_value=user)
        oauth2.model.User.by_email = MagicMock(return_value=[user] if user_exists else [])

        returned_username, returned_user = helper.identify(OAUTH2TOKEN)

        self.assertEqual(username, returned_username)
        self.assertEqual(user, returned_user)

        oauth2.model.User.by_email.assert_called_once_with(email)

        if not user_exists:
            oauth2.model.User.assert_called_once_with(email=email)
        else:
            self.assertEqual(0, oauth2.model.User.called)

        self.assertEqual(username, user.name)
        self.assertEqual(email, user.email)
        if sysadmin is not None:
            self.assertEqual(sysadmin, user.sysadmin)

        if fullname and fullname_field:
            self.assertEqual(fullname, user.fullname)
        else:
            self.assertEqual(None, user.fullname)

        oauth2.model.Session.add.assert_called_once_with(user)
        oauth2.model.Session.commit.assert_called_once()
        oauth2.model.Session.remove.assert_called_once()

    def test_identify_jwt(self):

        helper = self._helper(jwt_enable=True)
        token = OAUTH2TOKEN
        user_data = {self._user_field: 'test_user', self._email_field: 'test@test.com'}

        oauth2.jwt.decode.return_value = user_data

        oauth2.model.Session = MagicMock()
        user = MagicMock()
        user.name = None
        user.email = None
        oauth2.model.User = MagicMock(return_value=user)
        oauth2.model.User.by_email = MagicMock(return_value=[user])

        returned_username, returned_user = helper.identify(token)

        self.assertEqual(user_data[self._user_field], returned_username)
        self.assertEqual(user, returned_user)

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
                self.assertEqual(user_info['error_description'], str(e))
            exception_risen = True

        self.assertTrue(exception_risen)

    @patch.dict(os.environ, {'OAUTHLIB_INSECURE_TRANSPORT': ''})
    def test_identify_invalid_cert(self):

        helper = self._helper()
        token = {'access_token': 'OAUTH_TOKEN'}

        with self.assertRaises(InsecureTransportError):
            with patch('ckanext.oauth2.oauth2.OAuth2Session') as oauth2_session_mock:
                oauth2_session_mock().get.side_effect = SSLError('(Caused by SSLError(SSLError("bad handshake: Error([(\'SSL routines\', \'tls_process_server_certificate\', \'certificate verify failed\')],)",),)')
                helper.identify(token)

    @patch.dict(os.environ, {'OAUTHLIB_INSECURE_TRANSPORT': ''})
    def test_identify_invalid_cert_legacy(self):

        helper = self._helper(conf={"ckan.oauth2.legacy_idm": "True"})
        token = {'access_token': 'OAUTH_TOKEN'}

        with self.assertRaises(InsecureTransportError):
            with patch('ckanext.oauth2.oauth2.requests.get') as requests_get_mock:
                requests_get_mock.side_effect = SSLError('(Caused by SSLError(SSLError("bad handshake: Error([(\'SSL routines\', \'tls_process_server_certificate\', \'certificate verify failed\')],)",),)')
                helper.identify(token)

    @patch.dict(os.environ, {'OAUTHLIB_INSECURE_TRANSPORT': ''})
    def test_identify_unexpected_ssl_error(self):

        helper = self._helper()
        token = {'access_token': 'OAUTH_TOKEN'}

        with self.assertRaises(SSLError):
            with patch('ckanext.oauth2.oauth2.OAuth2Session') as oauth2_session_mock:
                oauth2_session_mock().get.side_effect = SSLError('unexpected error')
                helper.identify(token)

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
        self.assertEqual(OAUTH2TOKEN, helper.get_stored_token('user'))

    @parameterized.expand([
        ({'came_from': 'http://localhost/dataset'}, ),
        ({},)
    ])
    def test_redirect_from_callback(self, identity):
        came_from = 'initial-page'
        state = b64encode(json.dumps({'came_from': came_from}).encode('utf-8')).decode('utf-8')
        oauth2.toolkit.request = make_request(True, 'data.com', 'callback', {'state': state, 'code': 'code'})

        helper = self._helper()
        helper.redirect_from_callback()

        oauth2.toolkit.redirect_to.assert_called_once_with(came_from)

    @parameterized.expand([
        (True, True),
        (True, False),
        (False, False),
        (False, True),
    ])
    def test_update_token(self, user_exists, jwt_expires_in):
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

        if jwt_expires_in:
            newtoken = {
                'access_token': 'new_access_token',
                'token_type': 'new_token_type',
                'expires_in': 'new_expires_in',
                'refresh_token': 'new_refresh_token'
            }
            helper.update_token('user', newtoken)

            oauth2.model.Session.add.assert_called_once()
            oauth2.model.Session.commit.assert_called_once()

            tk = oauth2.model.Session.add.call_args_list[0][0][0]
            self.assertEqual(user, tk.user_name)
            self.assertEqual(newtoken['access_token'], tk.access_token)
            self.assertEqual(newtoken['token_type'], tk.token_type)
            self.assertEqual(newtoken['expires_in'], tk.expires_in)
            self.assertEqual(newtoken['refresh_token'], tk.refresh_token)
        else:
            newtoken = {
                'access_token': 'new_access_token',
                'token_type': 'new_token_type',
                'refresh_token': 'new_refresh_token'
            }
            expires_in_data = {'exp': 3600, 'iat': 0}
            # Mock _decode_jwt instead of jwt.decode
            helper._decode_jwt = MagicMock(return_value=expires_in_data)
            helper.update_token('user', newtoken)

            oauth2.model.Session.add.assert_called_once()
            oauth2.model.Session.commit.assert_called_once()

            tk = oauth2.model.Session.add.call_args_list[0][0][0]
            self.assertEqual(user, tk.user_name)
            self.assertEqual(newtoken['access_token'], tk.access_token)
            self.assertEqual(newtoken['token_type'], tk.token_type)
            self.assertEqual(3600, tk.expires_in)
            self.assertEqual(newtoken['refresh_token'], tk.refresh_token)

    @parameterized.expand([
        (True,),
        (False,)
    ])
    @patch.dict(os.environ, {'OAUTHLIB_INSECURE_TRANSPORT': '', 'REQUESTS_CA_BUNDLE': ''})
    def test_refresh_token(self, user_exists):
        username = 'user'
        helper = self.helper = self._helper()

        if user_exists:
            current_token = OAUTH2TOKEN
        else:
            current_token = None

        helper.get_stored_token = MagicMock(return_value=current_token)
        helper.update_token = MagicMock()

        newtoken = {
            'access_token': 'new_access_token',
            'token_type': 'new_token_type',
            'expires_in': 'new_expires_in',
            'refresh_token': 'new_refresh_token'
        }
        session = MagicMock()
        session.refresh_token = MagicMock(return_value=newtoken)
        oauth2.OAuth2Session = MagicMock(return_value=session)

        result = helper.refresh_token(username)

        if user_exists:
            self.assertEqual(newtoken, result)
            helper.get_stored_token.assert_called_once_with(username)
            oauth2.OAuth2Session.assert_called_once_with(helper.client_id, token=current_token, scope=helper.scope)
            session.refresh_token.assert_called_once_with(helper.token_endpoint, client_secret=helper.client_secret, client_id=helper.client_id, verify=True)
            helper.update_token.assert_called_once_with(username, newtoken)
        else:
            self.assertIsNone(result)
            self.assertEqual(0, oauth2.OAuth2Session.call_count)
            self.assertEqual(0, session.refresh_token.call_count)
            self.assertEqual(0, helper.update_token.call_count)

    @patch.dict(os.environ, {'OAUTHLIB_INSECURE_TRANSPORT': ''})
    def test_refresh_token_invalid_cert(self):
        username = 'user'
        current_token = OAUTH2TOKEN
        helper = self._helper()

        helper.get_stored_token = MagicMock(return_value=current_token)

        with self.assertRaises(InsecureTransportError):
            with patch('ckanext.oauth2.oauth2.OAuth2Session') as oauth2_session_mock:
                oauth2_session_mock().refresh_token.side_effect = SSLError('(Caused by SSLError(SSLError("bad handshake: Error([(\'SSL routines\', \'tls_process_server_certificate\', \'certificate verify failed\')],)",),)')
                helper.refresh_token(username)

    @patch.dict(os.environ, {'OAUTHLIB_INSECURE_TRANSPORT': ''})
    def test_refresh_token_unexpected_ssl_error(self):
        username = 'user'
        current_token = OAUTH2TOKEN
        helper = self._helper()

        helper.get_stored_token = MagicMock(return_value=current_token)

        with self.assertRaises(SSLError):
            with patch('ckanext.oauth2.oauth2.OAuth2Session') as oauth2_session_mock:
                oauth2_session_mock().refresh_token.side_effect = SSLError('unexpected error')
                helper.refresh_token(username)

    def test_unwrap_response(self):
        helper = self._helper()
        data = {'result': {'user': {'name': 'test', 'email': 'test@test.com'}}}
        self.assertEqual({'name': 'test', 'email': 'test@test.com'}, helper._unwrap_response(data, 'result.user'))
        self.assertEqual(data, helper._unwrap_response(data, None))
        self.assertEqual(data, helper._unwrap_response(data, ''))

    @patch('ckanext.oauth2.oauth2.login_user')
    def test_log_user_into_ckan(self, mock_login_user):
        helper = self._helper()
        user_obj = MagicMock()
        helper.log_user_into_ckan(user_obj)
        mock_login_user.assert_called_once_with(user_obj)

    def test_decode_jwt_unverified(self):
        helper = self._helper()
        token_data = {'username': 'test', 'email': 'test@test.com'}
        oauth2.jwt.decode = MagicMock(return_value=token_data)
        result = helper._decode_jwt('some.jwt.token', verify=False)
        self.assertEqual(token_data, result)
        oauth2.jwt.decode.assert_called_once_with(
            'some.jwt.token',
            options={"verify_signature": False, "verify_exp": False}
        )
