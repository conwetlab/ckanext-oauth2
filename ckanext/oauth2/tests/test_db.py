import unittest
import ckanext.oauth2.db as db

from mock import MagicMock


class DBTest(unittest.TestCase):

    def setUp(self):
        # Restart databse initial status
        db.UserToken = None

        # Create mocks
        self._sa = db.sa
        db.sa = MagicMock()

    def tearDown(self):
        db.UserToken = None
        db.sa = self._sa

    def test_initdb_not_initialized(self):

        # Call the function
        model = MagicMock()
        db.init_db(model)

        # Assert that table method has been called
        db.sa.Table.assert_called_once()
        model.meta.mapper.assert_called_once()

    def test_initdb_initialized(self):
        db.UserToken = MagicMock()

        # Call the function
        model = MagicMock()
        db.init_db(model)

        # Assert that table method has been called
        self.assertEquals(0, db.sa.Table.call_count)
        self.assertEquals(0, model.meta.mapper.call_count)
