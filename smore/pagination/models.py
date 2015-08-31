import abc
import math
import collections

import six


class BasePage(six.with_metaclass(abc.ABCMeta, collections.Sequence)):
    """A page of results.
    """
    def __init__(self, paginator, results):
        self.paginator = paginator
        self.results = results

    def __len__(self):
        return len(self.results)

    def __getitem__(self, index):
        return self.results[index]

    @abc.abstractproperty
    def info(self):
        pass


class OffsetPage(BasePage):

    def __init__(self, paginator, page, results):
        self.page = page
        super(OffsetPage, self).__init__(paginator, results)

    @property
    def info(self):
        return {
            'page': self.page,
            'count': self.paginator.count,
            'pages': self.paginator.pages,
            'per_page': self.paginator.per_page,
        }


class SeekPage(BasePage):

    @property
    def last_indexes(self):
        if self.results:
            return self.paginator._get_index_values(self.results[-1])
        return None

    @property
    def info(self):
        return {
            'count': self.paginator.count,
            'pages': self.paginator.pages,
            'per_page': self.paginator.per_page,
            'last_indexes': self.last_indexes,
        }


class BasePaginator(six.with_metaclass(abc.ABCMeta, object)):

    def __init__(self, cursor, per_page, count=None):
        self.cursor = cursor
        self.per_page = per_page
        self.count = count or self._count()

    @abc.abstractproperty
    def page_type(self):
        pass

    @property
    def pages(self):
        return int(math.ceil(self.count / self.per_page))

    @abc.abstractproperty
    def get_page(self):
        pass

    @abc.abstractmethod
    def _count(self):
        pass


class OffsetPaginator(BasePaginator):
    """Paginator based on offsets and limits. Not performant for large result sets.
    """
    page_type = OffsetPage

    def get_page(self, page):
        offset, limit = self.per_page * (page - 1), self.per_page
        return self.page_type(self, page, self._fetch(offset, limit))

    @abc.abstractmethod
    def _fetch(self, offset, limit):
        pass


class SeekPaginator(BasePaginator):
    """Paginator using keyset pagination for performance on large result sets.
    See http://use-the-index-luke.com/no-offset for details.
    """
    page_type = SeekPage

    def __init__(self, cursor, per_page, index_column, sort_column=None, sort_direction=None,
                 count=None):
        self.index_column = index_column
        self.sort_column = sort_column
        self.sort_direction = sort_direction
        super(SeekPaginator, self).__init__(cursor, per_page, count=count)

    def get_page(self, last_index=None, sort_index=None):
        limit = self.per_page
        return self.page_type(self, self._fetch(last_index, sort_index, limit))

    @abc.abstractmethod
    def _fetch(self, last_index, sort_index, limit):
        pass

    @abc.abstractmethod
    def _get_index_values(self, result):
        """Get index values from last result, to be used in seeking to the next
        page. Optionally include sort values, if any.
        """
        pass
