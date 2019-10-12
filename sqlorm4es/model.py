# -*- coding: utf-8 -*-
# @Time    : 2019/10/3 22:46
# @Author  : floatsliang
# @File    : model.py
from six import add_metaclass
from copy import copy, deepcopy

from .epool import POOL
from .sql import SelectSQL, InsertSQL, DeleteSQL, UpdateSQL
from .field import Field, FieldDescriptor
from .utils import result_wrapper


class ModelOptions(object):

    def __init__(self, name, bases, attrs):
        self.index = attrs.get('__index__', name)
        self.database = attrs.get('__database__', {})
        self.doc_type = attrs.get('__doc_type__', '_doc')


class ModelMeta(type):

    def __new__(mcs, name, bases, attrs):
        if not bases:
            return super(ModelMeta, mcs).__new__(mcs, name, bases, attrs)

        for b in bases:
            if hasattr(b, '_data'):
                for attr_name, attr in b.__dict__.items():
                    if isinstance(attr, FieldDescriptor) and attr_name not in attrs:
                        attrs[attr_name] = deepcopy(attr)

        cls = super(ModelMeta, mcs).__new__(mcs, name, bases, attrs)
        cls._meta = ModelOptions(name, bases, attrs)
        cls._data = {}
        cls._fields = {}

        for name, attr in cls.__dict__.items():
            if isinstance(attr, Field):
                if not attr.get_name():
                    attr.set_name(name)
                field_desc = FieldDescriptor(attr)
                setattr(cls, name, field_desc)
                attr = field_desc
            if isinstance(attr, FieldDescriptor):
                if attr.field.default:
                    cls._data[name] = attr.field.default
                cls._fields[name] = attr
        return cls


@add_metaclass(ModelMeta)
class BaseModel(object):

    def __init__(self, *args, **kwargs):
        self._meta = copy(self.__class__._meta)
        self._data = copy(self.__class__._data)
        if 'index' in kwargs:
            self.index(kwargs['index'])
        if 'database' in kwargs:
            self.database(kwargs['database'])

        for k, v in kwargs.items():
            if k in self._fields:
                setattr(self, k, v)

    def index(self, index):
        self._meta.index = index

    def database(self, database):
        self._meta.database = database

    def get_index(self):
        return self._meta.index

    def get_database(self):
        return self._meta.database

    @classmethod
    def select(cls, *fields):
        return SelectSQL(cls).fields(*fields)

    @classmethod
    def update(cls, **fields_map):
        return UpdateSQL(cls, columns=fields_map)

    @classmethod
    def delete(cls):
        return DeleteSQL(cls)

    @classmethod
    def insert(cls, *rows):
        return InsertSQL(cls, values=rows)

    @classmethod
    @result_wrapper
    def get_many(cls, fields: list, index=None, where=None, database=None, **kwargs):
        result = SelectSQL(cls,
                           index=index,
                           database=database,
                           **kwargs)\
            .fields(*fields)\
            .where(where)\
            .limit(kwargs.get('limit'), None)\
            .offset(kwargs.get('offset', None)).execute()
        return result

    @classmethod
    @result_wrapper
    def get_one(cls, fields: list, index=None, where=None, database=None, **kwargs):
        kwargs['limit'] = 1
        return cls.get_many(fields=fields, index=index, where=where, database=database, **kwargs)

    def save(self):
        pass


