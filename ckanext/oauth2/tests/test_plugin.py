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

import unittest
import ckanext.oauth2.plugin as plugin

from unittest.mock import MagicMock, patch
from parameterized import parameterized

CUSTOM_AUTHORIZATION_HEADER = 'x-auth-token'
OAUTH2_AUTHORIZATION_HEADER = 'authorization'
HOST = 'ckan.example.org'


class PluginTest(unittest.TestCase):

    def setUp(self):
        # Save functions and mock them
        self._toolkit = plugin.toolkit
        plugin.toolkit = MagicMock()
        plugin.toolkit.config = {'ckan.oauth2.authorization_header': OAUTH2_AUTHORIZATION_HEADER}

        self._oauth2_helper = plugin.oauth2_helper
        plugin.oauth2_helper = MagicMock()

        # Create the plugin
        self._plugin = plugin.OAuth2Plugin()
        self._plugin.update_config(plugin.toolkit.config)

    def tearDown(self):
        # Unmock functions
        plugin.toolkit = self._toolkit
        plugin.oauth2_helper = self._oauth2_helper

    def _set_identity(self, identity):
        plugin.toolkit.request.environ = {}
        if identity:
            plugin.toolkit.request.environ['repoze.who.identity'] = {'repoze.who.userid': identity}

    def test_get_blueprint(self):
        # Test that get_blueprint returns a list with the blueprint
        blueprints = self._plugin.get_blueprint()
        self.assertIsInstance(blueprints, list)
        self.assertEqual(len(blueprints), 1)

    def test_auth_functions(self):

        EXPECTED_AUTH_FUNCTIONS = ['user_create', 'user_update', 'user_reset', 'request_reset']

        auth_functions = self._plugin.get_auth_functions()

        for auth_function in auth_functions:
            self.assertIn(auth_function, EXPECTED_AUTH_FUNCTIONS)
            function_result = auth_functions[auth_function]({'user': 'test'}, {})
            self.assertIn('success', function_result)
            self.assertEqual(False, function_result['success'])

    @parameterized.expand([
        ({},                                              None,                      None,    None,    False),
        ({},                                              None,                      None,    None,    True),

        ({},                                              None,                      'test',  'test',  False),
        ({},                                              None,                      'test',  'test',  True),

        ({'invalid_header': 'api_key'},                   None,                      None,    None,    False),
        ({'invalid_header': 'api_key'},                   None,                      'test2', 'test2', False),
        ({'invalid_header': 'api_key'},                   None,                      None,    None,    True),
        ({'invalid_header': 'api_key'},                   None,                      'test2', 'test2', True),

        ({OAUTH2_AUTHORIZATION_HEADER: 'Bearer api_key'}, 'test',                    None,    'test',  True),
        ({OAUTH2_AUTHORIZATION_HEADER: 'Bearer api_key'}, 'test',                    'test2', 'test',  True),
        ({OAUTH2_AUTHORIZATION_HEADER: 'Bearer api_key'}, ValueError('Invalid Key'), 'test2', 'test2', True),
        ({OAUTH2_AUTHORIZATION_HEADER: 'Bearer api_key'}, ValueError('Invalid Key'), None,    None,    True),
        ({OAUTH2_AUTHORIZATION_HEADER: 'Bearer api_key'}, None,                      'test2', 'test2', True),
        ({OAUTH2_AUTHORIZATION_HEADER: 'Otherr api_key'}, None,                      None,    None,    True),
        ({OAUTH2_AUTHORIZATION_HEADER: 'api_key'},        None,                      'test2', 'test2', True),
        ({OAUTH2_AUTHORIZATION_HEADER: 'api_key'},        None,                      None,    None,    True),

        ({CUSTOM_AUTHORIZATION_HEADER: 'api_key'},        'test',                    None,    'test',  False),
        ({CUSTOM_AUTHORIZATION_HEADER: 'api_key'},        'test',                    'test2', 'test',  False),
        ({CUSTOM_AUTHORIZATION_HEADER: 'api_key'},        ValueError('Invalid Key'), 'test2', 'test2', False),
        ({CUSTOM_AUTHORIZATION_HEADER: 'api_key'},        ValueError('Invalid Key'), None,    None,    False),
        ({CUSTOM_AUTHORIZATION_HEADER: 'api_key'},        None,                      'test2', 'test2', False),

    ])
    @patch("ckanext.oauth2.plugin.g")
    def test_identify(self, headers, authenticate_result, identity, expected_user, oauth2, g_mock):

        if not oauth2:
            plugin.toolkit.config = {'ckan.oauth2.authorization_header': CUSTOM_AUTHORIZATION_HEADER}
            self._plugin.update_config(plugin.toolkit.config)

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

        self._plugin.oauth2helper.identify = MagicMock(side_effect=authenticate_side_effect)
        self._plugin.oauth2helper.get_stored_token = MagicMock(return_value=usertoken)
        self._plugin.oauth2helper.refresh_token = MagicMock(return_value=newtoken)

        # Authentication header is not included
        plugin.toolkit.request.headers = headers

        # Call the function
        self._plugin.identify()

        # Check that the function "authenticate" (called when the API Key is included) has not been called
        if oauth2 and OAUTH2_AUTHORIZATION_HEADER in headers and headers[OAUTH2_AUTHORIZATION_HEADER].startswith('Bearer '):
            token = headers[OAUTH2_AUTHORIZATION_HEADER].replace('Bearer ', '')
            self._plugin.oauth2helper.identify.assert_called_once_with({'access_token': token})
        elif not oauth2 and CUSTOM_AUTHORIZATION_HEADER in headers:
            self._plugin.oauth2helper.identify.assert_called_once_with({'access_token': headers[CUSTOM_AUTHORIZATION_HEADER]})
        else:
            self.assertEqual(0, self._plugin.oauth2helper.identify.call_count)

        self.assertEqual(expected_user, g_mock.user)

        if expected_user is None:
            self.assertFalse(hasattr(g_mock, 'usertoken') and g_mock.usertoken is not None)
        else:
            self.assertEqual(usertoken, g_mock.usertoken)

            # method 'usertoken_refresh' should relay on the one provided by the repoze.who module
            g_mock.usertoken_refresh()
            self._plugin.oauth2helper.refresh_token.assert_called_once_with(expected_user)
            self.assertEqual(newtoken, g_mock.usertoken)
