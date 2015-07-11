# -*- coding: utf-8 -*-

from smore.pagination import models


class ListPage(models.BasePage):
    info = {}


class Bunch(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class TestPage:

    def test_length(self):
        page = ListPage(None, range(20))
        assert len(page) == 20

    def test_get_item(self):
        page = ListPage(None, range(5))
        assert page[2] == 2


class TestOffsetPage:

    def test_info(self):
        fake_paginator = Bunch(count=50, pages=5, per_page=10)
        page = models.OffsetPage(fake_paginator, 3, range(50))
        info = {
            'page': 3,
            'count': 50,
            'pages': 5,
            'per_page': 10,
        }
        assert page.info == info


class TestSeekPage:

    def test_info(self):
        _get_index_values = lambda *a, **kw: 42
        fake_paginator = Bunch(count=50, pages=5, per_page=10, _get_index_values=_get_index_values)
        page = models.SeekPage(fake_paginator, range(50))
        info = {
            'count': 50,
            'pages': 5,
            'per_page': 10,
            'last_indexes': 42,
        }
        assert page.info == info
