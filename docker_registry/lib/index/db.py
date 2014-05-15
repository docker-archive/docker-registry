# -*- coding: utf-8 -*-

"""An SQLAlchemy backend for the search endpoint
"""

import sqlalchemy
import sqlalchemy.exc
import sqlalchemy.ext.declarative
import sqlalchemy.orm
import sqlalchemy.sql.functions

from ... import storage
from .. import config
from . import Index


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
        sqlalchemy.String, nullable=False, unique=True)
    description = sqlalchemy.Column(sqlalchemy.String)

    def __repr__(self):
        return "<{0}(name='{1}', description='{2}')>".format(
            type(self).__name__, self.name, self.description)


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
        self._engine = sqlalchemy.create_engine(database)
        self._session = sqlalchemy.orm.sessionmaker(bind=self._engine)
        self.version = 1
        self._setup_database()
        super(SQLAlchemyIndex, self).__init__()

    def _setup_database(self):
        session = self._session()
        try:
            version = session.query(
                sqlalchemy.sql.functions.max(Version.id)).first()[0]
        except sqlalchemy.exc.OperationalError:
            version = None
        if version:
            if version != self.version:
                raise NotImplementedError(
                    'unrecognized search index version {0}'.format(version))
        else:
            self._generate_index(session=session)
        session.close()

    def _generate_index(self, session):
        store = storage.load()
        Base.metadata.create_all(self._engine)
        session.add(Version(id=self.version))
        for repository in self._walk_storage(store=store):
            session.add(Repository(**repository))
        session.commit()

    def _handle_repository_created(
            self, sender, namespace, repository, value):
        name = '{0}/{1}'.format(namespace, repository)
        description = ''  # TODO(wking): store descriptions
        session = self._session()
        session.add(Repository(name=name, description=description))
        session.commit()
        session.close()

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

    def _handle_repository_deleted(self, sender, namespace, repository):
        name = '{0}/{1}'.format(namespace, repository)
        session = self._session()
        session.query(Repository).filter(Repository.name == name).delete()
        session.commit()
        session.close()

    def results(self, search_term):
        session = self._session()
        like_term = '%%%s%%' % search_term
        repositories = session.query(Repository).filter(
            sqlalchemy.sql.or_(
                Repository.name.like(like_term),
                Repository.description.like(like_term)))
        return [
            {
                'name': repo.name,
                'description': repo.description,
            }
            for repo in repositories]
