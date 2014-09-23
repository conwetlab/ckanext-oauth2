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
import ckanext.oauth2.plugin as plugin

from mock import MagicMock
from nose_parameterized import parameterized

AUTHORIZATION_HEADER = 'Custom_Header'


class PluginTest(unittest.TestCase):

    def setUp(self):
        # Save functions and mock them
        self._config = plugin.config
        plugin.config = {'ckan.oauth2.authorization_header': AUTHORIZATION_HEADER}

        self._toolkit = plugin.toolkit
        plugin.toolkit = MagicMock()

        self._session = plugin.session
        plugin.session = MagicMock()

        self._oauth2 = plugin.oauth2
        plugin.oauth2 = MagicMock()

        # Create the plugin
        self._plugin = plugin.OAuth2Plugin()

    def tearDown(self):
        # Unmock functions
        plugin.config = self._config
        plugin.toolkit = self._toolkit
        plugin.session = self._session

    def _set_identity(self, identity):
        plugin.toolkit.request.environ = {}
        if identity:
            plugin.toolkit.request.environ['repoze.who.identity'] = {'repoze.who.userid': identity}

    @parameterized.expand([
        (),
        ('a'),
        (None, 'a',),
        (None, None, 'a'),
        ('a', 'b', 'c')
    ])
    def test_before_map(self, register_url=None, reset_url=None, edit_url=None):

        # Setup the config dictionary
        plugin.config = {}

        if register_url:
            plugin.config['ckan.oauth2.register_url'] = register_url

        if reset_url:
            plugin.config['ckan.oauth2.reset_url'] = reset_url

        if edit_url:
            plugin.config['ckan.oauth2.edit_url'] = edit_url

        # In this case we need a own instance of the plugin, so we create it
        self._plugin = plugin.OAuth2Plugin()

        # Create the mapper (mock) and call the function
        mapper = MagicMock()
        self._plugin.before_map(mapper)

        # Check that the mapper has been called correctly
        mapper.connect.assert_called_with('/oauth2/callback',
                                          controller='ckanext.oauth2.controller:OAuth2Controller',
                                          action='callback')

        if register_url:
            mapper.redirect.assert_any_call('/user/register', register_url)

        if reset_url:
            mapper.redirect.assert_any_call('/user/reset', reset_url)

        if edit_url:
            mapper.redirect.assert_any_call('/user/edit/{user}', edit_url)

    def test_auth_functions(self):

        EXPECTED_AUTH_FUNCTIONS = ['user_create', 'user_update', 'user_reset', 'request_reset']

        auth_functions = self._plugin.get_auth_functions()

        for auth_function in auth_functions:
            self.assertIn(auth_function, EXPECTED_AUTH_FUNCTIONS)
            function_result = auth_functions[auth_function]({'user': 'test'}, {})
            self.assertIn('success', function_result)
            self.assertEquals(False, function_result['success'])

    @parameterized.expand([
        (),
        ({},                                None,                          'test',  'test'),
        ({AUTHORIZATION_HEADER: 'api_key'}, {'repoze.who.userid': 'test'}, None,    'test'),
        ({AUTHORIZATION_HEADER: 'api_key'}, {'repoze.who.userid': 'test'}, 'test2', 'test'),
        ({AUTHORIZATION_HEADER: 'api_key'}, ValueError('Invalid KEY'),     'test2', 'test2'),
        ({AUTHORIZATION_HEADER: 'api_key'}, None,                          'test2', 'test2'),
        ({'invalid_header': 'api_key'},     {'repoze.who.userid': 'test'}, None,    None),
        ({'invalid_header': 'api_key'},     {'repoze.who.userid': 'test'}, 'test2', 'test2'),
    ])
    def test_identify(self, headers={}, authenticate_result=None, identity=None, expected_user=None):

        self._set_identity(identity)

        usertoken = {
            'access_token': 'current_access_token',
            'refresh_token': 'current_refresh_token',
            'token_type': 'current_token_type',
            'expires_in': '2678399'
        }
        newtoken = {
            'access_token': 'new_access_token',
            'refresh_token': 'new_refresh_token',
            'token_type': 'new_token_type',
            'expires_in': '3600'
        }

        def authenticate_side_effect(identity):
            if isinstance(authenticate_result, Exception):
                raise authenticate_result
            else:
                return authenticate_result

        plugin.oauth2.OAuth2Helper.return_value.authenticate.side_effect = authenticate_side_effect
        plugin.oauth2.OAuth2Helper.return_value.get_token = MagicMock(return_value=usertoken)
        plugin.oauth2.OAuth2Helper.return_value.refresh_token = MagicMock(return_value=newtoken)

        # Authentication header is not included
        plugin.toolkit.request.headers = headers

        # The identify function must set the user id in this variable
        plugin.toolkit.c.user = None
        plugin.toolkit.c.usertoken = None
        plugin.toolkit.c.usertoken_refresh = None

        # Call the function
        self._plugin.identify()

        # Check that the function "authenticate" (called when the API Key is included) has not been called
        if headers and AUTHORIZATION_HEADER in headers:
            plugin.oauth2.OAuth2Helper.return_value.authenticate.assert_called_once_with({'oauth2.token': {'access_token': headers[AUTHORIZATION_HEADER]}})
        else:
            self.assertEquals(0, plugin.oauth2.OAuth2Helper.return_value.authenticate.call_count)

        self.assertEquals(expected_user, plugin.toolkit.c.user)
        plugin.session.save.assert_called_once()

        if expected_user is None:
            self.assertIsNone(plugin.toolkit.c.usertoken)
            self.assertIsNone(plugin.toolkit.c.usertoken_refresh)
        else:
            self.assertEquals(usertoken, plugin.toolkit.c.usertoken)

            # method 'usertoken_refresh' should relay on the one provided by the repoze.who module
            plugin.toolkit.c.usertoken_refresh()
            plugin.oauth2.OAuth2Helper.return_value.refresh_token.assert_called_once_with(expected_user)
            self.assertEquals(newtoken, plugin.toolkit.c.usertoken)

    @parameterized.expand([
        (),
        ('test'),
        (None, '/about'),
        ('test', '/about')
    ])
    def test_login(self, user=None, referer=None):

        expected_referer = '/' if referer is None else referer

        # The login function will check this variables
        plugin.toolkit.c.user = user
        plugin.toolkit.request.headers = {}
        if referer:
            plugin.toolkit.request.headers['Referer'] = referer

        # Call the function
        self._plugin.login()

        if not user:
            plugin.oauth2.OAuth2Helper.return_value.challenge.assert_called_once_with()
        else:
            self.assertEquals(0, plugin.toolkit.abort.call_count)
            plugin.toolkit.redirect_to.assert_called_with(bytes(expected_referer))
