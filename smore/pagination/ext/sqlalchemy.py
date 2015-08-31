# -*- coding: utf-8 -*-

from __future__ import absolute_import

import sqlalchemy as sa

from smore.pagination import models


class SqlalchemyMixin(object):

    def _count(self):
        return self.cursor.count()


class SqlalchemyOffsetPaginator(SqlalchemyMixin, models.OffsetPaginator):

    def _fetch(self, offset, limit):
        offset += (self.cursor._offset or 0)
        if self.cursor._limit:
            limit = min(limit, self.cursor._limit - offset)
        return self.cursor.offset(offset).limit(limit).all()


class SqlalchemySeekPaginator(SqlalchemyMixin, models.SeekPaginator):

    def _fetch(self, last_index, sort_index=None, limit=None):
        cursor = self.cursor
        direction = self.sort_direction or sa.asc
        lhs, rhs = (), ()
        if sort_index is not None:
            lhs += (self.sort_column, )
            rhs += (sort_index, )
        if last_index is not None:
            lhs += (self.index_column, )
            rhs += (last_index, )
        if any(rhs):
            filter = lhs > rhs if direction == sa.asc else lhs < rhs
            cursor = cursor.filter(filter)
        return cursor.order_by(
            direction(self.index_column)
        ).limit(
            limit
        ).all()

    def _get_index_values(self, result):
        ret = {'index': getattr(result, self.index_column.key)}
        if self.sort_column:
            key = self.sort_column.key
            ret[key] = getattr(result, self.sort_column.key)
        return ret
