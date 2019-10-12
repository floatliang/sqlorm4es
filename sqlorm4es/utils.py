# -*- coding: utf-8 -*-
# @Time    : 2019/10/11 9:45
# @Author  : floatsliang
# @File    : utils.py
from functools import wraps
from copy import deepcopy


class SearchResult(dict):

    def __init__(self, res: dict = None):
        super(SearchResult, self).__init__(data=[], meta={
            'count': 0,
            'status': 200,
            'error': 'ok'
        })
        if res:
            self.init(res)

    def init(self, res: dict):
        if 'hits' in res:
            self['data'] = res['hits']['hits']
            self['meta']['count'] = res['hits']['total']['value']
        elif 'error' in res:
            self['meta']['status'] = res['status']
            self['meta']['error'] = res['error']['reason']

    def __add__(self, other):
        if isinstance(other, SearchResult):
            res = SearchResult()
            if self['meta']['count'] > 0 or other['meta']['count'] > 0:
                res['data'] = deepcopy(self['data']) + deepcopy(other['data'])
                res['meta'] = {
                    'count': len(res['data']),
                    'status': 200,
                    'error': 'ok'
                }
            else:
                res['meta'] = deepcopy(self['meta'])
            return res
        else:
            raise ValueError(u'ERROR: right side of + operator should be SearchResult type')

    def __iadd__(self, other):
        if isinstance(other, SearchResult):
            if other['meta']['count'] > 0:
                self['data'] += other['data']
                self['meta'] = {
                    'count': len(self['data']),
                    'status': 200,
                    'error': 'ok'
                }
            return self
        else:
            raise ValueError(u'ERROR: right side of += operator should be SearchResult type')


def result_wrapper(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        return SearchResult(func(*args, **kwargs))
    return wrapped
