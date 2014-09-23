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
import ckanext.oauth2.controller as controller
import json

from base64 import b64decode, b64encode
from mock import MagicMock
from nose_parameterized import parameterized

RETURNED_STATUS = 302
EXAMPLE_FLASH = 'This is a test'
EXCEPTION_MSG = 'Invalid'
CAME_FROM_FIELD = 'came_from'


class OAuth2PluginTest(unittest.TestCase):

    def setUp(self):
        # Save the response, the request and the helper functions and mock them
        self._helpers = controller.helpers
        controller.helpers = MagicMock()

        self._oauth2 = controller.oauth2
        controller.oauth2 = MagicMock()

        self._toolkit = controller.toolkit
        controller.toolkit = MagicMock()

        self.controller = controller.OAuth2Controller()

    def tearDown(self):
        # Unmock the function
        controller.helpers = self._helpers
        controller.oauth2 = self._oauth2
        controller.toolkit = self._toolkit

    def generate_state(self, url):
        return b64encode(bytes(json.dumps({CAME_FROM_FIELD: url})))

    def get_came_from(self, state):
        return json.loads(b64decode(state)).get(CAME_FROM_FIELD, '/')

    def test_controller_no_errors(self):
        oauth2Helper = controller.oauth2.OAuth2Helper.return_value

        token = {'oauth2.token': 'TOKEN'}
        identity = {'repoze.who.userid': 'user_id'}
        oauth2Helper.identify.return_value = token
        oauth2Helper.authenticate.return_value = identity

        # Call the controller
        self.controller.callback()

        oauth2Helper.identify.assert_called_once()
        oauth2Helper.authenticate.assert_called_once_with(token)
        oauth2Helper.remember.assert_called_once_with(identity)
        oauth2Helper.update_token.assert_called_once_with(identity['repoze.who.userid'], token['oauth2.token'])
        oauth2Helper.redirect_from_callback.assert_called_once_with(identity)

    @parameterized.expand([
        (),
        ('/',),
        ('/about', EXAMPLE_FLASH, EXAMPLE_FLASH)
    ])
    def test_controller_errors(self, came_from=None, error_description=None, expected_flash=EXCEPTION_MSG):

        # Recover function
        controller.oauth2.get_came_from = self.get_came_from

        oauth2Helper = controller.oauth2.OAuth2Helper.return_value
        oauth2Helper.identify.side_effect = Exception(EXCEPTION_MSG)

        controller.toolkit.request.GET = {}
        controller.toolkit.request.GET['state'] = self.generate_state(came_from)
        if error_description is not None:
            controller.toolkit.request.GET['error_description'] = error_description
        controller.toolkit.request.params.get = controller.toolkit.request.GET.get

        # Call the controller
        self.controller.callback()

        # Check the state and the location
        self.assertEquals(RETURNED_STATUS, controller.toolkit.response.status_int)
        self.assertEquals(came_from, controller.toolkit.response.location)
        controller.helpers.flash_error.assert_called_once_with(expected_flash)
