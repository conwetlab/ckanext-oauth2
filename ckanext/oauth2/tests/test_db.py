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
import ckanext.oauth2.db as db

from unittest.mock import MagicMock, patch


class DBTest(unittest.TestCase):

    def setUp(self):
        # Restart database initial status
        db.UserToken = None

        # Create mocks
        self._sa = db.sa
        db.sa = MagicMock()

        self._model = db.model
        db.model = MagicMock()

        self._domain_object = db.domain_object
        db.domain_object = MagicMock()

        self._mapper_registry = db._mapper_registry
        db._mapper_registry = MagicMock()

    def tearDown(self):
        db.UserToken = None
        db.sa = self._sa
        db.model = self._model
        db.domain_object = self._domain_object
        db._mapper_registry = self._mapper_registry

    def test_initdb_not_initialized(self):
        # Call the function
        db.init_db()

        # Assert that table and map_imperatively have been called
        db.sa.Table.assert_called_once()
        db._mapper_registry.map_imperatively.assert_called_once()

    def test_initdb_initialized(self):
        db.UserToken = MagicMock()

        # Call the function
        db.init_db()

        # Assert that table method has NOT been called
        self.assertEqual(0, db.sa.Table.call_count)
        self.assertEqual(0, db._mapper_registry.map_imperatively.call_count)
