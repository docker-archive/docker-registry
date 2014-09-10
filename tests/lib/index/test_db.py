import unittest

import mock

from docker_registry.lib.index import db


class TestVersion(unittest.TestCase):

    def setUp(self):
        self.version = db.Version()

    def test_repr(self):
        self.assertEqual(type(repr(self.version)), str)


class TestRepository(unittest.TestCase):

    def setUp(self):
        self.repository = db.Repository()

    def test_repr(self):
        self.assertEqual(type(repr(self.repository)), str)


class TestSQLAlchemyIndex(unittest.TestCase):

    def setUp(self):
        self.index = db.SQLAlchemyIndex(database="sqlite://")

    @mock.patch('sqlalchemy.engine.Engine.has_table', return_value=True)
    @mock.patch('sqlalchemy.orm.query.Query.first')
    def test_setup_database(self, first, has_table):
        first = mock.Mock(  # noqa
            side_effect=db.sqlalchemy.exc.OperationalError)
        self.assertRaises(
            NotImplementedError, db.SQLAlchemyIndex, database="sqlite://")
