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
DEFAULT_MESSAGE = 'It was impossible to log in you using the OAuth2 Service'
EXAMPLE_FLASH = 'This is a test'
CAME_FROM_FIELD = 'came_from'


class OAuth2PluginTest(unittest.TestCase):

    def setUp(self):

        self.controller = controller.OAuth2Controller()

        # Save the response, the request and the helper functions and mock them
        self._response = controller.response
        controller.response = MagicMock()

        self._request = controller.request
        controller.request = MagicMock()

        self._helpers = controller.helpers
        controller.helpers = MagicMock()

    def tearDown(self):
        # Unmock the function
        controller.response = self._response
        controller.request = self._request
        controller.helpers = self._helpers

    def generate_state(self, url):
        return b64encode(bytes(json.dumps({CAME_FROM_FIELD: url})))

    def get_came_from(self, state):
        return json.loads(b64decode(state)).get(CAME_FROM_FIELD, '/')

    @parameterized.expand([
        (),
        ('/',),
        ('/about', EXAMPLE_FLASH, EXAMPLE_FLASH)
    ])
    def test_controller(self, came_from=None, error_description=None, expected_flash=DEFAULT_MESSAGE):

        controller.request.GET = {}
        controller.request.GET['state'] = self.generate_state(came_from)
        if error_description is not None:
            controller.request.GET['error_description'] = error_description
        controller.request.params.get = controller.request.GET.get

        # Call the controller
        self.controller.callback()

        # Check the state and the location
        self.assertEquals(RETURNED_STATUS, controller.response.status_int)
        self.assertEquals(came_from, controller.response.location)
        controller.helpers.flash_error.assert_called_once_with(expected_flash)
