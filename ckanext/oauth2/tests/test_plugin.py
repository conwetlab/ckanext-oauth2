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
# ckanext/oauth2/tests/test_plugin.py
import pytest
from unittest.mock import MagicMock, patch
from ckanext.oauth2.plugin import OAuth2Plugin, toolkit
import ckanext.oauth2.plugin as plugin
from ckanext.oauth2.plugin import user_create, user_update, user_reset, request_reset
from flask import Flask, g

# Constants
CUSTOM_AUTHORIZATION_HEADER = 'x-auth-token'
OAUTH2_AUTHORIZATION_HEADER = 'authorization'
HOST = 'ckan.example.org'

# Create a MagicMock object to represent a user
user_mock = MagicMock()
user_mock.name = 'test_user'
user_mock.is_authenticated = True

# Mock OAuth2Helper class for testing
class MockOAuth2Helper:
    def __init__(self):
        pass

    def identify(self, token):
        return "test_user"

    def get_stored_token(self, user_name):
        return {
            'access_token': 'mocked_access_token',
            'refresh_token': 'mocked_refresh_token',
            'token_type': 'mocked_token_type',
            'expires_in': '3600'
        }

    def refresh_token(self, user_name):
        return {
            'access_token': 'refreshed_access_token',
            'refresh_token': 'refreshed_refresh_token',
            'token_type': 'refreshed_token_type',
            'expires_in': '3600'
        }

# Test cases for the OAuth2Plugin class methods
class TestOAuth2Plugin:
    @pytest.fixture
    def app(self):
        # Create a Flask app to establish an application context
        app = Flask(__name__)
        app.config['CKAN_ENV'] = 'test'  # Set the CKAN environment to 'test'
        return app

    def test_identify(self, plugin_setup, app):
        with app.app_context():
            plugin_instance = plugin_setup

            # Mock authentication to simulate an authenticated user
            with patch('flask_login.utils._get_user', return_value=user_mock):
                # Call the identify function
                plugin_instance.identify()
                assert str(g.user) == 'test_user'  # Adjust the expected user based on your changes

# ... (rest of the code)

# Additional test cases for auth functions
class TestAuthFunctions:

    def test_user_create(self):
        context = {'user': 'test_user'}
        data_dict = {}

        # Update this based on the changes in plugin.py
        result = user_create(context, data_dict)
        assert not result['success']
        assert result['msg'] == "Users cannot be created."

    def test_user_update(self):
        context = {'user': 'test_user'}
        data_dict = {}

        result = user_update(context, data_dict)
        assert not result['success']
        assert result['msg'] == "Users cannot be edited."

    def test_user_reset(self):
        context = {'user': 'test_user'}
        data_dict = {}

        result = user_reset(context, data_dict)
        assert not result['success']
        assert result['msg'] == "Users cannot reset passwords."

    def test_request_reset(self):
        context = {'user': 'test_user'}
        data_dict = {}

        result = request_reset(context, data_dict)
        assert not result['success']
        assert result['msg'] == "Users cannot reset passwords."

# Fixture for setting up the plugin
@pytest.fixture
def plugin_setup():
    original_toolkit = plugin.toolkit
    original_oauth2 = plugin.OAuth2Helper

    plugin.toolkit = MagicMock()
    plugin.toolkit.config = {'ckan.oauth2.authorization_header': OAUTH2_AUTHORIZATION_HEADER}
    plugin.OAuth2Helper = MockOAuth2Helper

    plugin_instance = plugin.OAuth2Plugin()
    plugin_instance.update_config(plugin.toolkit.config)

    yield plugin_instance

    plugin.toolkit = original_toolkit
    plugin.OAuth2Helper = original_oauth2

