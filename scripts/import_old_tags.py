#!/usr/bin/env python

import os
import sys

root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(root_path, 'lib'))

import storage


# Copy/Pasted from old models

from sqlalchemy import create_engine, ForeignKey, UniqueConstraint
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Table, Column, Integer, String, DateTime, func


Base = declarative_base()


class User(Base):

    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    username = Column(String(256), nullable=False, unique=True)
    email = Column(String(256), nullable=False, unique=True)
    password = Column(String(64), nullable=False)

    repositories = relationship(
        'Repository', order_by='Repository.name', backref='user'
    )


repositories_revisions = Table(
    'repositories_revisions',
    Base.metadata,
    Column('repository_id', Integer, ForeignKey('repositories.id')),
    Column('revision_id', String(64), ForeignKey('revisions.id'))
)


class Tag(Base):

    __tablename__ = 'tags'
    __table_args__ = (
        UniqueConstraint('name', 'repository_id'),
    )

    id = Column(Integer, primary_key=True)
    name = Column(String(256), nullable=False)
    revision_id = Column(String(64), ForeignKey('revisions.id'))
    repository_id = Column(Integer, ForeignKey('repositories.id'))
    revision = relationship('ImageRevision')


class ImageRevision(Base):

    __tablename__ = 'revisions'

    id = Column(String(64), primary_key=True, autoincrement=False, unique=True)
    parent_id = Column(String(64), index=True, nullable=True)
    layer_url = Column(String(256), index=False, nullable=True)
    created_at = Column(DateTime, nullable=False)


class Repository(Base):

    __tablename__ = 'repositories'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    name = Column(String(64), index=True, nullable=False)

    revisions = relationship(
        ImageRevision,
        secondary=repositories_revisions,
        order_by=ImageRevision.created_at.desc(),
        backref='repositories'
    )
    tags = relationship('Tag', order_by='Tag.name', backref='repository')


def import_tags(sess, store):
    for tag in sess.query(Tag).all():
        try:
            repos_name = tag.repository.name
            tag_name = tag.name
            repos_namespace = tag.repository.user.username
            image_id = tag.revision.id
            path = store.tag_path(repos_namespace, repos_name, tag_name)
            if store.exists(path):
                continue
            dest = store.put_content(path, image_id)
            print '{0} -> {1}'.format(dest, image_id)
        except AttributeError as e:
            print '# Warning: {0}'.format(e)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print 'Usage: {0} URL'.format(sys.argv[0])
        sys.exit(0)
    url = sys.argv[1]
    Session = sessionmaker(bind=create_engine(url))
    store = storage.load()
    sess = Session()
    import_tags(sess, store)
