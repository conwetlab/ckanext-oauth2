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

from base64 import b64decode, b64encode
import unittest
import json

from unittest.mock import MagicMock, patch
from parameterized import parameterized

from ckanext.oauth2 import views, plugin


RETURNED_STATUS = 302
EXAMPLE_FLASH = 'This is a test'
EXCEPTION_MSG = 'Invalid'
CAME_FROM_FIELD = 'came_from'


class CompleteException(Exception):
    description = 'Exception description'
    error = 'Exception error'


class ErrorException(Exception):
    error = 'Exception error 2'


class VoidException(Exception):
    pass


class OAuth2ViewsTest(unittest.TestCase):

    def setUp(self):
        self._helpers = views.helpers
        views.helpers = MagicMock()

        self._get_oauth2helper = views._get_oauth2helper
        self._oauth2helper = MagicMock()
        views._get_oauth2helper = MagicMock(return_value=self._oauth2helper)

        self._toolkit_views = views.toolkit
        self._toolkit_plugin = plugin.toolkit
        plugin.toolkit = views.toolkit = MagicMock()

        self._model = views.model
        views.model = MagicMock()

        self._get_came_from = views.get_came_from
        self._get_previous_page = views._get_previous_page

    def tearDown(self):
        views.helpers = self._helpers
        views._get_oauth2helper = self._get_oauth2helper
        views.toolkit = self._toolkit_views
        views.model = self._model
        views.get_came_from = self._get_came_from
        views._get_previous_page = self._get_previous_page
        plugin.toolkit = self._toolkit_plugin

    def generate_state(self, url):
        return b64encode(json.dumps({CAME_FROM_FIELD: url}).encode('utf-8')).decode('utf-8')

    def get_came_from(self, state):
        if not state:
            return '/'
        if isinstance(state, str):
            state = state.encode('utf-8')
        return json.loads(b64decode(state)).get(CAME_FROM_FIELD, '/')

    def test_callback_no_errors(self):
        token = 'TOKEN'
        user_id = 'user_id'
        user_obj = MagicMock()
        self._oauth2helper.get_token.return_value = token
        self._oauth2helper.identify.return_value = (user_id, user_obj)

        views.callback()

        self._oauth2helper.get_token.assert_called_once()
        self._oauth2helper.identify.assert_called_once_with(token)
        self._oauth2helper.log_user_into_ckan.assert_called_once_with(user_obj)
        self._oauth2helper.update_token.assert_called_once_with(user_id, token)
        self._oauth2helper.redirect_from_callback.assert_called_once_with()

    @parameterized.expand([
        (),
        ('/',),
        ('/', CompleteException(EXCEPTION_MSG), None, EXCEPTION_MSG),
        ('/', CompleteException(), None, str(CompleteException())),
        ('/', ErrorException(EXCEPTION_MSG), None, EXCEPTION_MSG),
        ('/', ErrorException(), None, str(ErrorException())),
        ('/', VoidException(EXCEPTION_MSG), None, EXCEPTION_MSG),
        ('/', VoidException(), None, 'VoidException'),
        ('/about', Exception(EXCEPTION_MSG), EXAMPLE_FLASH, EXAMPLE_FLASH)
    ])
    def test_callback_errors(self, came_from=None, exception=Exception(EXCEPTION_MSG),
                               error_description=None, expected_flash=EXCEPTION_MSG):

        views.get_came_from = self.get_came_from

        self._oauth2helper.get_token.side_effect = exception

        args_dict = {}
        args_dict['state'] = self.generate_state(came_from)
        if error_description is not None:
            args_dict['error_description'] = error_description

        views.toolkit.request.args = MagicMock()
        views.toolkit.request.args.get = lambda key, default='': args_dict.get(key, default)

        views.callback()

        # Verify session rollback on error
        views.model.Session.rollback.assert_called_once()
        views.helpers.flash_error.assert_called_once_with(expected_flash)

    @parameterized.expand([
        (),
        (None,                        None,               '/'),
        ('/about',                    None,               '/about'),
        ('/about',                    '/ckan-admin',      '/ckan-admin'),
        (None,                        '/ckan-admin',      '/ckan-admin'),
        ('/',                         None,               '/'),
        ('/user/logged_out_redirect', None,               '/'),
        ('/',                         '/ckan-admin',      '/ckan-admin'),
        ('/user/logged_out_redirect', '/ckan-admin',      '/ckan-admin'),
        ('http://google.es',          None,               '/'),
        ('http://google.es',          None,               '/')
    ])
    def test_login(self, referer=None, came_from=None, expected_referer='/'):

        views.toolkit.request.headers = {}
        views.toolkit.request.args = {}
        views.toolkit.request.scheme = 'http'
        views.toolkit.request.host = 'localhost'

        if referer:
            views.toolkit.request.headers['Referer'] = referer

        if came_from:
            views.toolkit.request.args = {'came_from': came_from}

        views._get_previous_page = lambda default: plugin._get_previous_page(default)

        views.login()

        self._oauth2helper.challenge.assert_called_once_with(expected_referer)
