# -*- coding: utf-8 -*-
# @Time    : 2019/10/4 22:53
# @Author  : floatsliang
# @File    : compiler.py
import re
from functools import partial

from .field import OP, Expr, Field
from .query import Q


def f_add(a, b):
    return b + a


def f_sub(a, b):
    return b - a


def f_mul(a, b):
    return b * a


def f_div(a, b):
    return b / a


class QueryCompiler(object):
    logical_op = {
        OP.OP_AND,
        OP.OP_OR,
    }

    math_op = {
        OP.OP_ADD,
        OP.OP_SUB,
        OP.OP_MUL,
        OP.OP_DIV,
        OP.OP_XOR,
    }

    rel_op = {
        OP.OP_EQ,
        OP.OP_LT,
        OP.OP_LTE,
        OP.OP_GT,
        OP.OP_GTE,
        OP.OP_NE,
        OP.OP_IN,
        OP.OP_LIKE,
    }

    agg_op = {
        OP.OP_MAX,
        OP.OP_MIN,
        OP.OP_AVG,
        OP.OP_COUNT,
        OP.OP_SUM,
    }

    _MAX_NEST_DEPTH = 10

    def __init__(self, sql):
        self._sql = sql

    def compile(self, sql_type='select'):
        if sql_type == 'select':
            return self.parse_select_sql()
        elif sql_type == 'insert':
            return self.parse_insert_sql()
        elif sql_type == 'update':
            return self.parse_update_sql()
        elif sql_type == 'delete':
            return self.parse_delete_sql()
        else:
            raise NotImplementedError(u'ERROR: sql type not implemented yet')

    def _op_to_func(self, q, op, inv=False):
        if op is OP.OP_AND:
            if inv:
                func = q.must_not
            else:
                func = q.must
        elif op is OP.OP_OR:
            func = q.should
        elif op is OP.OP_LT:
            func = q.lt
        elif op is OP.OP_LTE:
            func = q.lte
        elif op is OP.OP_GT:
            func = q.gt
        elif op is OP.OP_GTE:
            func = q.gte
        elif op is OP.OP_EQ:
            func = q.value
        elif op is OP.OP_NE:
            func = q.value
        elif op is OP.OP_IN:
            func = q.value
        elif op is OP.OP_ADD:
            func = f_add
        elif op is OP.OP_SUB:
            func = f_sub
        elif op is OP.OP_MUL:
            func = f_mul
        elif op is OP.OP_DIV:
            func = f_div
        elif op is OP.OP_COUNT:
            func = partial(q.metrics, op='count')
        elif op is OP.OP_MAX:
            func = partial(q.metrics, op='max')
        elif op is OP.OP_MIN:
            func = partial(q.metrics, op='min')
        elif op is OP.OP_SUM:
            func = partial(q.metrics, op='sum')
        elif op is OP.OP_AVG:
            func = partial(q.metrics, op='avg')
        else:
            raise NotImplementedError

        return func

    def parse_where(self, scoring=True):
        """
        preorder AND/OR node bi-tree to construct nested Bool query
        :return:
        """
        curr_node = self._sql['where']
        where_query = Q('bool', scoring=scoring)
        if curr_node.op not in self.logical_op:
            root_op = OP.OP_AND
        else:
            root_op = curr_node.op
        curr_query = [where_query, root_op]
        node_stack = []
        q_stack = []

        while node_stack or curr_node:
            if curr_node.op in self.logical_op:
                op = curr_node.op
                if curr_node.op is not curr_query[1]:
                    logical_func = self._op_to_func(curr_query[0], curr_query[1])
                    new_q = Q('bool')
                    logical_func(new_q)
                    q_stack.append(curr_query)
                    if len(q_stack) > self._MAX_NEST_DEPTH:
                        raise Exception(
                            u'ERROR: nested AND/OR operator exceeds max depth: {}'.format(self._MAX_NEST_DEPTH))
                    curr_query = [new_q, op]
                node_stack.append([curr_node.rhs, op])
                curr_node = curr_node.lhs
            else:
                leaf, inv = self.parse_expr(curr_node)
                if curr_query[1] is OP.OP_OR and inv is True:
                    new_q = Q('bool')
                    leaf = self._op_to_func(new_q, OP.OP_AND, inv)(leaf)
                logical_func = self._op_to_func(curr_query[0], curr_query[1], inv)
                logical_func(leaf)
                if len(node_stack) == 0:
                    break
                curr_node, op = node_stack.pop()
                if op != curr_query[1]:
                    curr_query = q_stack.pop()

        return where_query

    def parse_expr(self, leaf_node):
        inv = False
        if isinstance(leaf_node, Expr):
            op = leaf_node.op
            if op in self.rel_op:
                l_val, l_inv = self.parse_expr(leaf_node.lhs)
                r_val, r_inv = self.parse_expr(leaf_node.rhs)
                if isinstance(l_val, Field):
                    field = l_val
                    field_name = field.get_name()
                    val = r_val
                    inv_val = l_inv
                elif isinstance(r_val, Field):
                    field = r_val
                    field_name = field.get_name()
                    val = l_val
                    inv_val = r_inv
                elif isinstance(l_val, str) and isinstance(r_val, str):
                    field = l_val
                    field_name = field
                    val = r_val
                    inv_val = l_inv
                else:
                    raise ValueError(
                        u'ERROR: left or right field of relation operation {} should be Field or str type'.format(op))
                if op in (OP.OP_LTE, OP.OP_LT, OP.OP_GT, OP.OP_GTE):
                    q = Q('range', field=field_name)
                elif op is OP.OP_EQ or op is OP.OP_NE:
                    q = Q('term', field=field_name)
                    if op is OP.OP_NE:
                        inv = True
                elif op is OP.OP_IN:
                    if not isinstance(val, list) and not isinstance(val, tuple):
                        val = re.sub(r'\s*[()\[\]]\s*', '', val)
                        val = re.split(r'\s*[,;]\s*', val)
                    q = Q('terms', field=field_name)
                    val = list(val)
                elif op is OP.OP_LIKE:
                    raise NotImplementedError
                else:
                    raise NotImplementedError
                if hasattr(field, 'validate'):
                    if isinstance(val, list):
                        val = [field.validate(v) for v in val]
                    else:
                        val = field.validate(val)
                if callable(inv_val):
                    if isinstance(val, list):
                        val = [inv_val(v) for v in val]
                    else:
                        val = inv_val(val)
                self._op_to_func(q, op)(val)

                return q, inv
            elif op in self.math_op:
                if isinstance(leaf_node.lhs, Field):
                    field = leaf_node.lhs
                    val = leaf_node.rhs
                elif isinstance(leaf_node.rhs, Field):
                    field = leaf_node.rhs
                    val = leaf_node.lhs
                else:
                    raise ValueError(u'ERROR: currently not support nested math operator')
                if op is OP.OP_ADD:
                    inv = partial(self._op_to_func(None, OP.OP_SUB), a=val)
                elif op is OP.OP_SUB:
                    inv = partial(self._op_to_func(None, OP.OP_ADD), a=val)
                elif op is OP.OP_MUL:
                    inv = partial(self._op_to_func(None, OP.OP_DIV), a=val)
                elif op is OP.OP_DIV:
                    inv = partial(self._op_to_func(None, OP.OP_MUL), a=val)

                return field, inv
            elif op in self.agg_op:
                field = leaf_node.lhs
                if isinstance(field, str):
                    pass
                elif isinstance(field, Field):
                    field = field.get_name()
                else:
                    raise ValueError(u'ERROR: aggregation field type only support str or Field')
                return (field, op), inv
            else:
                raise NotImplementedError
        else:
            return leaf_node, inv

    def parse_fields(self):
        fields = self._sql['fields']
        _source_fields = []
        _agg_fields = []
        for field in fields:
            if isinstance(field, Field):
                _source_fields.append(field.get_name())
            elif isinstance(field, str):
                _source_fields.append(field)
            elif isinstance(field, Expr):
                if field.op not in self.agg_op:
                    raise ValueError(u'ERROR: unsupported aggregation operator in fields')
                _agg_fields.append(self.parse_expr(field)[0])
            else:
                raise ValueError(u'ERROR: unsupported field type {} in fields'.format(field.__class__))
        return _source_fields, _agg_fields

    def parse_group_by(self):
        fields = self._sql['group_by']
        _agg_fields = []
        for field in fields:
            if isinstance(field, Field):
                _agg_fields.append(field.get_name())
            elif isinstance(field, str):
                _agg_fields.append(field)
            else:
                raise ValueError(u'ERROR: unsupported field type {} in group by'.format(field.__class__))
        return _agg_fields

    def parse_order_by(self):
        return self._sql['order_by']

    def parse_join(self, query):
        pass

    def parse_select_sql(self):
        query = Q('dsl')

        where_query = self.parse_where()
        query.query(where_query)
        self.parse_join(where_query)

        _source_fields, _agg_fields_selection = self.parse_fields()
        _agg_fields_group_by = self.parse_group_by()
        _sort_fields = self.parse_order_by()
        curr_agg = query
        prev_name = ''
        if _agg_fields_group_by:
            for field in _agg_fields_group_by:
                agg_query = Q('aggs')
                if field in _sort_fields:
                    agg_query.terms(field=field, order_by="_key", order=_sort_fields[field])
                else:
                    agg_query.terms(field=field)
                curr_agg.aggs(agg_query, name=prev_name)
                curr_agg = agg_query
                prev_name = field
        if _agg_fields_selection:
            agg_query = Q('aggs')
            curr_agg.aggs(agg_query, name=prev_name)
            curr_agg = agg_query
            for field_and_op in _agg_fields_selection:
                field, op = field_and_op
                self._op_to_func(curr_agg, op)(field)

        if _source_fields:
            query._source(_source_fields)
        for field, order in _sort_fields.items():
            query.sort(Q('sort', field=field, order=order))

        if self._sql['limit']:
            query.size(self._sql['limit'])
        if self._sql['offset']:
            query.offset(self._sql['offset'])

        return query

    def parse_update_sql(self):
        pass

    def parse_insert_sql(self):
        pass

    def parse_delete_sql(self):
        pass
