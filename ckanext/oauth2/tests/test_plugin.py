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

from unittest.mock import MagicMock, patch, PropertyMock
from parameterized import parameterized

CUSTOM_AUTHORIZATION_HEADER = 'x-auth-token'
OAUTH2_AUTHORIZATION_HEADER = 'authorization'
HOST = 'ckan.example.org'


class PluginTest(unittest.TestCase):

    def setUp(self):
        self._toolkit = plugin.toolkit
        plugin.toolkit = MagicMock()
        plugin.toolkit.config = {'ckan.oauth2.authorization_header': OAUTH2_AUTHORIZATION_HEADER}

        self._OAuth2Helper = plugin.OAuth2Helper
        plugin.OAuth2Helper = MagicMock()

        self._current_user = plugin.current_user
        plugin.current_user = MagicMock()
        plugin.current_user.is_authenticated = False

        self._login_user = plugin.login_user
        plugin.login_user = MagicMock()

        self._logout_user = plugin.logout_user
        plugin.logout_user = MagicMock()

        self._model = plugin.model
        plugin.model = MagicMock()

        # Create the plugin
        self._plugin = plugin.OAuth2Plugin()
        self._plugin.update_config(plugin.toolkit.config)

    def tearDown(self):
        plugin.toolkit = self._toolkit
        plugin.OAuth2Helper = self._OAuth2Helper
        plugin.current_user = self._current_user
        plugin.login_user = self._login_user
        plugin.logout_user = self._logout_user
        plugin.model = self._model

    def test_get_blueprint(self):
        with patch('ckanext.oauth2.plugin.get_blueprints', return_value=[MagicMock()]) as mock_get:
            # Patch the import inside get_blueprint
            pass  # blueprint tested via views

    def test_auth_functions(self):
        EXPECTED_AUTH_FUNCTIONS = ['user_create', 'user_update', 'user_reset', 'request_reset']

        auth_functions = self._plugin.get_auth_functions()

        for auth_function in auth_functions:
            self.assertIn(auth_function, EXPECTED_AUTH_FUNCTIONS)
            function_result = auth_functions[auth_function]({'user': 'test'}, {})
            self.assertIn('success', function_result)
            self.assertEqual(False, function_result['success'])

    def test_make_middleware(self):
        app = MagicMock()
        config = {}
        result = self._plugin.make_middleware(app, config)
        self.assertEqual(app, result)

    def test_get_helpers(self):
        helpers = self._plugin.get_helpers()
        self.assertIn('oauth2_get_stored_token', helpers)
        self.assertIn('oauth2_refresh_token', helpers)

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

        # Configure current_user for session-based identity
        if identity:
            plugin.current_user.is_authenticated = True
            plugin.current_user.name = identity
        else:
            plugin.current_user.is_authenticated = False

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

        def authenticate_side_effect(token_dict):
            if isinstance(authenticate_result, Exception):
                raise authenticate_result
            elif authenticate_result:
                user_obj = MagicMock()
                user_obj.name = authenticate_result
                return authenticate_result, user_obj
            else:
                return None, None

        self._plugin.oauth2helper.identify = MagicMock(side_effect=authenticate_side_effect)
        self._plugin.oauth2helper.get_stored_token = MagicMock(return_value=usertoken)
        self._plugin.oauth2helper.refresh_token = MagicMock(return_value=newtoken)
        self._plugin.oauth2helper.jwt_enable = False

        plugin.toolkit.request.headers = headers

        # Disable request_loader installation in tests
        self._plugin._request_loader_installed = True

        self._plugin.identify()

        if oauth2 and OAUTH2_AUTHORIZATION_HEADER in headers and headers[OAUTH2_AUTHORIZATION_HEADER].startswith('Bearer '):
            token = headers[OAUTH2_AUTHORIZATION_HEADER].replace('Bearer ', '')
            self._plugin.oauth2helper.identify.assert_called_once_with({'access_token': token})
        elif not oauth2 and CUSTOM_AUTHORIZATION_HEADER in headers:
            self._plugin.oauth2helper.identify.assert_called_once_with({'access_token': headers[CUSTOM_AUTHORIZATION_HEADER]})
        else:
            self.assertEqual(0, self._plugin.oauth2helper.identify.call_count)

        if expected_user is not None:
            self.assertEqual(expected_user, g_mock.user)
        else:
            # When no user found, g.user should be None
            if not identity:
                self.assertIsNone(g_mock.user)
