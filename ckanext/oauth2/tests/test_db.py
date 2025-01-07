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
import pytest
from unittest.mock import MagicMock
from ckanext.oauth2.db import UserToken

@pytest.fixture
def setup_mocks():
    # Create mocks
    yield

def test_user_token_creation():
    # Create a UserToken object
    access_token= 'access_token_value',
    token_type= 'bearer',
    refresh_token= 'refresh_token_value',
    expires_in= 3600
    
    user_token = UserToken('test_user', access_token, token_type, refresh_token, expires_in)

    # Check if the object is created correctly
    assert user_token.user_name == 'test_user'
    assert user_token.access_token == access_token
    assert user_token.token_type == token_type
    assert user_token.refresh_token == refresh_token
    assert user_token.expires_in == 3600

def test_user_token_by_user_name(setup_mocks):
    # Mocking the query method
    query_mock = MagicMock()
    UserToken.by_user_name = MagicMock(return_value=query_mock)

    # Call the function
    user_token = UserToken.by_user_name('test_user')

    # Assert that the class method was called with the correct argument
    UserToken.by_user_name.assert_called_once_with('test_user')
    
    # Clean up
    UserToken.by_user_name.reset_mock()

