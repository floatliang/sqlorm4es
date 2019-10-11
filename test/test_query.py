# -*- coding: utf-8 -*-
# @Time    : 2019/10/9 20:48
# @Author  : floatsliang
# @File    : test_query.py
from sqlorm4es.query import *

query = {
    "query": {
        "bool": {
            "must": [
                {
                    "terms": {
                        "city.keyword": [
                            "北京",
                            "深圳"
                        ]
                    }
                },
                {
                    "term": {
                        "academic.keyword": {
                            "value": "本科"
                        }
                    }
                },
                {
                    "bool": {
                        "should": [
                            {
                                "term": {
                                    "content.keyword": {
                                        "value": "ES"
                                    }
                                }
                            },
                            {
                                "term": {
                                    "position.keyword": {
                                        "value": "ES"
                                    }
                                }
                            },
                        ]
                    }
                }
            ]
        }
    },
    "size": 10,
    "from": 0
}


def test_Q_proxy():
    assert (isinstance(Q('dsl'), Dsl) and isinstance(Q('bool'), Bool) and
            isinstance(Q('term', field='lala'), Term) and isinstance(Q('terms', field='lolo'), Terms) and
            isinstance(Q('match', field='meme'), Match) and isinstance(Q('range', field='ww'), Range) and
            isinstance(Q('sort', field='ddd'), Sort) and isinstance(Q('aggs'), Aggs))
    q = Q('dsl')
    assert Q(q) is q
    q = {
        'bool': {}
    }
    assert Q(q) is not q


def test_construct_query():
    dsl = Q('dsl', q=query)
    assert dsl == query
    dsl._source(["f", "s", "dd"])\
        .sort(Q('sort', field='dfad').order('desc'))\
        .offset(23)\
        .aggs(Q('aggs').terms(field='ss', name='test'))
    dsl.get_query()\
        .should(Q('match', field='lala').analyzer('dfad'))\
        .filter(Q('bool').minimum_should_match(2))\
        .must([Q('match', field='dd').query('dd').analyzer('standard'), {'term': {'dd': {'value': 'dd'}}}])\
        .range(field='tt', go_to='must_not', order='desc')


