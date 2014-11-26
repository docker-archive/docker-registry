# -*- coding: utf-8 -*-

"""An SQLAlchemy backend for the search endpoint
"""

import logging

from ... import storage
from ... import toolkit
from .. import config
from . import Index
import sqlalchemy
import sqlalchemy.exc
import sqlalchemy.ext.declarative
import sqlalchemy.orm
import sqlalchemy.sql.functions


logger = logging.getLogger(__name__)


Base = sqlalchemy.ext.declarative.declarative_base()


class Version (Base):
    "Schema version for the search-index database"
    __tablename__ = 'version'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)

    def __repr__(self):
        return '<{0}(id={1})>'.format(type(self).__name__, self.id)


class Repository (Base):
    "Repository description"
    __tablename__ = 'repository'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    name = sqlalchemy.Column(
        sqlalchemy.String(length=30 + 1 + 64),  # namespace / respository
        nullable=False, unique=True)
    description = sqlalchemy.Column(
        sqlalchemy.String(length=100))

    def __repr__(self):
        return "<{0}(name='{1}', description='{2}')>".format(
            type(self).__name__, self.name, self.description)


def retry(f):
    def _retry(self, *args, **kwargs):
        retry_times = 1
        i = 0
        while True:
            try:
                return f(self, *args, **kwargs)
            except sqlalchemy.exc.DBAPIError as e:
                if i < retry_times:
                    logger.warn("DB is disconnected. Reconnect to it.")
                    self.reconnect_db()
                    i += 1
                else:
                    raise e

    return _retry


class SQLAlchemyIndex (Index):
    """Maintain an index of repository data

    The index is a dictionary.  The keys are
    '{namespace}/{repository}' strings, and the values are description
    strings.  For example:

      index['library/ubuntu'] = 'An ubuntu image...'
    """
    def __init__(self, database=None):
        if database is None:
            cfg = config.load()
            database = cfg.sqlalchemy_index_database
        self._database = database
        self._engine = sqlalchemy.create_engine(database)
        self._session = sqlalchemy.orm.sessionmaker(bind=self._engine)
        self.version = 1
        self._setup_database()
        super(SQLAlchemyIndex, self).__init__()

    def reconnect_db(self):
        self._engine = sqlalchemy.create_engine(self._database)
        self._session = sqlalchemy.orm.sessionmaker(bind=self._engine)

    @toolkit.exclusive_lock
    def _setup_database(self):
        session = self._session()
        if self._engine.has_table(table_name=Version.__tablename__):
            version = session.query(
                sqlalchemy.sql.functions.max(Version.id)).first()[0]
        else:
            version = None
        if version:
            if version != self.version:
                raise NotImplementedError(
                    'unrecognized search index version {0}'.format(version))
        else:
            self._generate_index(session=session)
        session.close()

    @retry
    def _generate_index(self, session):
        store = storage.load()
        Base.metadata.create_all(self._engine)
        session.add(Version(id=self.version))
        for repository in self._walk_storage(store=store):
            session.add(Repository(**repository))
        session.commit()

    @retry
    def _handle_repository_created(
            self, sender, namespace, repository, value):
        name = '{0}/{1}'.format(namespace, repository)
        description = ''  # TODO(wking): store descriptions
        session = self._session()
        session.add(Repository(name=name, description=description))
        session.commit()
        session.close()

    @retry
    def _handle_repository_updated(
            self, sender, namespace, repository, value):
        name = '{0}/{1}'.format(namespace, repository)
        description = ''  # TODO(wking): store descriptions
        session = self._session()
        session.query(Repository).filter(
            Repository.name == name
        ).update(
            values={'description': description},
            synchronize_session=False
        )
        session.commit()
        session.close()

    @retry
    def _handle_repository_deleted(self, sender, namespace, repository):
        name = '{0}/{1}'.format(namespace, repository)
        session = self._session()
        session.query(Repository).filter(Repository.name == name).delete()
        session.commit()
        session.close()

    @retry
    def results(self, search_term=None):
        session = self._session()
        repositories = session.query(Repository)
        if search_term:
            like_term = '%%%s%%' % search_term
            repositories = repositories.filter(
                sqlalchemy.sql.or_(
                    Repository.name.like(like_term),
                    Repository.description.like(like_term)))
        results = [
            {
                'name': repo.name,
                'description': repo.description,
            }
            for repo in repositories]
        session.close()
        return results
