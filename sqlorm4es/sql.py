# -*- coding: utf-8 -*-
# @Time    : 2019/10/4 18:22
# @Author  : floatsliang
# @File    : sql.py
from typing import Union
import re
from copy import deepcopy

from .epool import POOL
from .compiler import QueryCompiler
from .field import Expr, Field, OP_DICT, OP
from .utils import result_wrapper, SearchResult

_WHERE_PATTERN = re.compile(
    r'^\s*(?P<lhs>\S+)\s*(?P<op>(=|!=|<>|>=|<=|>|<|in|IN|LIKE|like|MATCH|match|MATCHALL|matchall))\s*(?P<rhs>\S+)\s*$')
_AGG_PATTERN = re.compile(
    r'^\s*(?P<aggs>(count|COUNT|sum|SUM|max|MAX|min|MIN|avg|AVG|distinct|DISTINCT))\(\s*(?P<field>\S+)\s*\)\s*$')
_ORDER_BY_PATTERN = re.compile(r'^\s*(?P<field>\S+),?(\s+(?P<order>(asc|ASC|desc|DESC)))?\s*$')


def where_str_to_expr_dict(expr_str: str) -> dict:
    expr_dict = {}
    op_list = [' = ', ' != ', ' >= ', ' <= ', ' > ', ' < ', ' <> ', ' in ', ' not like ', ' like ', ' not match ',
               ' match ', ' matchall ']
    expr_str_lower = expr_str.lower()
    for op in op_list:
        op_idx = expr_str_lower.find(op)
        if op_idx >= 0:
            expr_dict['op'] = op.strip()
            expr_dict['lhs'] = expr_str[:op_idx].strip()
            expr_dict['rhs'] = expr_str[op_idx + len(op):].strip()
            break
    return expr_dict


def parse_where(node: str):
    match_dict = where_str_to_expr_dict(node)
    if match_dict:
        if match_dict['op'].lower() not in OP_DICT:
            raise NotImplementedError(u'ERROR: {} operation not supported in str type'.format(match_dict['op']))
        return Expr(match_dict['lhs'], OP_DICT[match_dict['op'].lower()], match_dict['rhs'])
    return None


def parse_where_tuple_expr(node: Union[tuple, list]):
    field = node[0].strip()
    op = node[1].lower().strip()
    values = node[2]
    if len(node) > 3:
        rel_op = node[3].lower().strip()
    else:
        rel_op = 'and'

    new_expr = None
    if op not in OP_DICT:
        raise NotImplementedError(u'ERROR: {} operation not supported in str type'.format(op))
    if not isinstance(values, (tuple, list)):
        values = [values]
    for val in values:
        if new_expr:
            new_expr = Expr(new_expr, OP_DICT[rel_op], Expr(field, OP_DICT[op], val))
        else:
            new_expr = Expr(field, OP_DICT[op], val)
    return new_expr


def parse_aggs(node: str):
    match_agg = _AGG_PATTERN.match(node)
    if match_agg:
        match_dict = match_agg.groupdict()
        if match_dict['aggs'].lower() not in OP_DICT:
            raise NotImplementedError(u'ERROR: {} aggregation not supported yet'.format(match_dict['aggs']))
        return Expr(match_dict['field'], OP_DICT[match_dict['aggs'].lower()], None)
    return None


def parse_order_by(order_by: str):
    match_order_by = _ORDER_BY_PATTERN.match(order_by)
    if match_order_by:
        match_dict = match_order_by.groupdict()
        agg = parse_aggs(match_dict['field'])
        if agg:
            match_dict['field'] = agg
        return match_dict['field'], match_dict.get('order', 'asc')
    return None


class SQL(object):

    def __init__(self, model_clazz, *args, **kwargs):
        self._model_clazz = model_clazz
        self._index = None
        self._database = None
        self._doc_type = None
        if model_clazz:
            meta = getattr(model_clazz, '_meta')
            if meta:
                self._index = getattr(meta, 'index', None)
                self._database = getattr(meta, 'database', None)
                self._doc_type = getattr(meta, 'doc_type', None)
        self._data['where'] = None
        self._index = kwargs.get('index', None) or self._index
        self._database = kwargs.get('database', None) or self._database
        self._doc_type = kwargs.get('doc_type', None) or self._doc_type
        self._compiler = QueryCompiler(self._data)

    def index(self, index):
        self._index = index
        return self

    def database(self, database):
        self._database = database
        return self

    def doc_type(self, doc_type):
        self._doc_type = doc_type
        return self

    def clone(self):
        new_sql = self.__class__(self._model_clazz)
        new_sql.index(self._index)
        new_sql.database(deepcopy(self._database))
        new_sql._data = deepcopy(self._data)
        new_sql._doc_type = self._doc_type
        new_sql._compiler = QueryCompiler(new_sql._data)
        return new_sql

    def where(self, *nodes):
        for node in nodes:
            if not isinstance(node, Expr):
                if isinstance(node, str):
                    node = parse_where(node)
                elif isinstance(node, (tuple, list)):
                    node = parse_where_tuple_expr(node)
                else:
                    raise ValueError(u'ERROR: node in where must be expression or str')
            if not node:
                raise AttributeError(u'ERROR: node cannot be NoneType, it may caused by parse failure')
            if not self._data['where']:
                self._data['where'] = node
            else:
                self._data['where'] &= node
        return self

    def compile(self):
        raise NotImplementedError

    def execute(self):
        raise NotImplementedError


class InsertSQL(SQL):

    def __init__(self, model_clazz, **kwargs):
        if not model_clazz:
            raise Exception(u'InsertSQL must have index Model')
        self._data = {'id': None, 'values': [], 'upsert': True, 'columns': model_clazz._fields}
        super(InsertSQL, self).__init__(model_clazz, **kwargs)

    def id(self, doc_id):
        self._data['id'] = doc_id
        return self

    def values(self, rows):
        pass

    def upsert(self, insert_on_conflict=True):
        self._data['upsert'] = insert_on_conflict
        return self

    def compile(self):
        pass

    def execute(self, ):
        pass


class DeleteSQL(SQL):

    def __init__(self, model_clazz, **kwargs):
        super(DeleteSQL, self).__init__(**kwargs)

    def compile(self):
        pass

    def execute(self):
        pass


class UpdateSQL(SQL):

    def __init__(self, model_clazz, **kwargs):
        super(UpdateSQL, self).__init__(**kwargs)

    def compile(self):
        pass

    def execute(self):
        pass


class SelectSQL(SQL):

    def __init__(self, model_clazz=None, **kwargs):
        self._data = {'fields': [], 'join': None, 'group_by': [], 'order_by': {}, 'limit': None, 'offset': None}
        super(SelectSQL, self).__init__(model_clazz, **kwargs)

    def fields(self, *fields):
        for field in fields:
            if isinstance(field, str):
                agg = parse_aggs(field)
                if agg:
                    field = agg
            elif isinstance(field, Field):
                field = field.get_name()
            self._data['fields'].append(field)
        return self

    def group_by(self, *fields):
        self._data['group_by'] += fields
        return self

    def order_by(self, *fields):
        for field_and_order in fields:
            if isinstance(field_and_order, tuple) or isinstance(field_and_order, list):
                field, order = field_and_order
                field = field.get_name() if isinstance(field, Field) else str(field)
                self._data['order_by'][field] = order
                continue
            field, order = parse_order_by(field_and_order)
            if not field:
                raise ValueError(u'ERROR: order by field {} cannot be parsed correctly'.format(field_and_order))
            self._data['order_by'][field] = order
        return self

    def limit(self, limit: int = 10):
        self._data['limit'] = int(limit)
        return self

    def offset(self, offset: int = 0):
        self._data['offset'] = int(offset)
        return self

    def join(self, join_type, on=None):
        return self

    def compile(self):
        return self._compiler.compile()

    def paginate(self):
        """
        yield document according to your sql and order by field
        :return:
        """
        if not self._data['limit'] or not self._data['order_by']:
            raise Exception(u'ERROR: paginate need page length(limit) and order by field')
        query = self.order_by(('_id', 'asc')).compile()
        database = POOL.connect(**self._database)
        res = database.search(index=self._index, body=query, doc_type=self._doc_type)
        if 'hits' not in res:
            return
        res_data = res['hits']['hits']
        if not res_data:
            return
        search_after_val = res_data[-1].get('sort', None)
        if search_after_val is None:
            return SearchResult(res)
        if 'from' in query:
            del query['from']
        query['search_after'] = search_after_val
        while 1:
            yield SearchResult(res)
            res = database.search(index=self._index, body=query, doc_type=self._doc_type)
            if 'hits' not in res:
                return
            res_data = res['hits']['hits']
            if not res_data:
                return
            query['search_after'] = res_data[-1]['sort']

    @result_wrapper
    def execute(self):
        query = self.compile()
        kwargs = {}
        if self._doc_type:
            kwargs['doc_type'] = self._doc_type
        return POOL.connect(**self._database).search(index=self._index, body=query, **kwargs)
