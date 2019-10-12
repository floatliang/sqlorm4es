# -*- coding: utf-8 -*-
# @Time    : 2019/10/9 23:03
# @Author  : floatsliang
# @File    : test_compiler.py
from sqlorm4es.compiler import QueryCompiler
from sqlorm4es.field import *
from sqlorm4es.model import BaseModel


class LogCenter(BaseModel):
    __index__ = 'lala'
    __database__ = {
        "host": "122.23.2.23"
    }

    ok = Boolean(default=True)
    lineno = Integer(required=True)
    message = Text(default='xixi')
    timestamp = Date(timezone="+8")
    bigbrother = Object(
        head=Integer(),
        body=Text(),
        leg=Date(),
        hand=Object(
            finger=Float(),
            nail=Boolean()
        )
    )


sql = {
    'fields': [LogCenter.ok, LogCenter.lineno, 'test', 'max(lineno)', LogCenter.timestamp],
    'where': ((LogCenter.ok == 'false') & (LogCenter.message != 'dfdf')) | (LogCenter.timestamp >= '2017-10-12') | (
                LogCenter.bigbrother.head >> ' ( 12; 45 ) '),
    'join': None,
    'group_by': [LogCenter.timestamp],
    'order_by': {'lineno': 'desc', 'timestamp': 'asc'},
    'limit': 22,
    'offset': 100
}

parser = QueryCompiler(sql)


def test_parse_where():
    bool_q = parser.parse_where()
    expected_q = {
      'bool': {
        'filter': {
          'bool': {
            'should': [
              {
                'bool': {
                  'must': [
                    {
                      'term': {
                        'ok': {
                          'value': 'false'
                        }
                      }
                    }
                  ],
                  'must_not': [
                    {
                      'term': {
                        'message': {
                          'value': 'dfdf'
                        }
                      }
                    }
                  ]
                }
              },
              {
                'range': {
                  'timestamp': {
                    'gte': '2017-10-12'
                  }
                }
              },
              {
                'terms': {
                  'bigbrother.head': [
                    'dfd',
                    'df'
                  ]
                }
              }
            ]
          }
        }
      }
    }
    assert bool_q == expected_q


def test_parse_fields():
    _source, _aggs = parser.parse_fields()
    assert _source == ['ok', 'lineno', 'test', 'timestamp']
    assert _aggs == [('lineno', OP.OP_MAX)]


def test_parse_group_by():
    _aggs = parser.parse_group_by()
    assert _aggs == ['timestamp']


def test_parse_order_by():
    _sort = parser.parse_order_by()
    assert _sort == {'lineno': 'desc', 'timestamp': 'asc'}


def test_parse_select_sql():
    q = parser.parse_select_sql()
    expected_aggs = {
        'group_by_timestamp': {
            'terms': {
                'field': 'timestamp',
                'order': {
                    '_key': 'asc'
                }
            }
        }
    }
    assert q['query'] == parser.parse_where()
    assert q['aggs'] == expected_aggs


