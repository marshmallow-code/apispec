# -*- coding: utf-8 -*-

import random

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base

from smore.pagination.ext import sqlalchemy as pa


Base = declarative_base()


class Album(Base):
    __tablename__ = 'album'
    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String)


@pytest.fixture
def session():
    engine = sa.create_engine('sqlite:///:memory:')
    Session = sa.orm.sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    return Session()


def random_string(chars):
    a, z = ord('a'), ord('z')
    return ''.join(chr(random.randint(a, z)) for _ in range(chars))


@pytest.fixture
def albums(session):
    ret = [
        Album(name=random_string(5))
        for _ in range(50)
    ]
    for each in ret:
        session.add(each)
    session.flush()
    return ret


class TestSqlalchemy:

    @pytest.mark.parametrize(['index'], [(1, ), (2, ), (3, )])
    def test_offset(self, session, albums, index):
        paginator = pa.SqlalchemyOffsetPaginator(session.query(Album), 20)
        page = paginator.get_page(index)
        start, stop = (index - 1) * 20, index * 20
        assert page.results == albums[start:stop]

    def test_seek(self, session, albums):
        paginator = pa.SqlalchemySeekPaginator(session.query(Album), 20, Album.id)
        page1 = paginator.get_page()
        page2 = paginator.get_page(last_index=page1.info['last_indexes']['index'])
        page3 = paginator.get_page(last_index=page2.info['last_indexes']['index'])
        assert page1.results == albums[:20]
        assert page2.results == albums[20:40]
        assert page3.results == albums[40:]

    def test_seek_sort_seek(self, session, albums):
        query = session.query(Album).order_by(Album.name)
        paginator = pa.SqlalchemySeekPaginator(query, 20, Album.id, Album.name, sa.asc)
        page1 = paginator.get_page()
        last_indexes = page1.info['last_indexes']
        page2 = paginator.get_page(
            last_index=last_indexes['index'],
            sort_index=last_indexes['name'],
        )
        last_indexes = page2.info['last_indexes']
        page3 = paginator.get_page(
            last_index=last_indexes['index'],
            sort_index=last_indexes['name'],
        )
        rows = session.query(Album).order_by(Album.name, Album.id).all()
        assert page1.results == rows[:20]
        assert page2.results == rows[20:40]
        assert page3.results == rows[40:]
