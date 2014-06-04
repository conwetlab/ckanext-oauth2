import unittest
import ckanext.oauth2.controller as controller
import json

from base64 import b64decode, b64encode
from mock import MagicMock
from nose_parameterized import parameterized

RETURNED_STATUS = 301
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
