# -*- coding: utf-8 -*-
# @Time    : 2019/10/3 22:46
# @Author  : floatsliang
# @File    : field.py
import json
from ast import literal_eval
from six import string_types
from datetime import datetime, date, timezone as dt_tz, timedelta
from dateutil import parser, tz

__all__ = ['OP', 'OP_DICT', 'Expr', 'Integer', 'Float', 'Boolean', 'Text', 'Date', 'Object']


class OP:
    OP_ADD = 1
    OP_SUB = 2
    OP_MUL = 3
    OP_DIV = 4
    OP_AND = 5
    OP_OR = 6
    OP_XOR = 7
    OP_EQ = 8
    OP_LT = 9
    OP_LTE = 10
    OP_GT = 11
    OP_GTE = 12
    OP_NE = 13
    OP_IN = 14
    OP_LIKE = 15

    OP_COUNT = 21
    OP_SUM = 22
    OP_MAX = 23
    OP_MIN = 24
    OP_AVG = 25


OP_DICT = {
    '<>': OP.OP_NE, '=': OP.OP_EQ, '>': OP.OP_GT,
    '>=': OP.OP_GTE, '<': OP.OP_LT, '<=': OP.OP_LTE,
    '!=': OP.OP_NE, 'in': OP.OP_IN, 'like': OP.OP_LIKE,
    'count': OP.OP_COUNT, 'sum': OP.OP_SUM, 'max': OP.OP_MAX,
    'avg': OP.OP_MAX,
}


def _e(op, inv=False):
    def inner(self, rhs):
        if inv:
            return Expr(rhs, op, self)
        return Expr(self, op, rhs)

    return inner


class Node(object):

    __and__ = _e(OP.OP_AND)
    __or__ = _e(OP.OP_OR)

    __add__ = _e(OP.OP_ADD)
    __sub__ = _e(OP.OP_SUB)
    __mul__ = _e(OP.OP_MUL)
    __div__ = _e(OP.OP_DIV)
    __xor__ = _e(OP.OP_XOR)
    __radd__ = _e(OP.OP_ADD, inv=True)
    __rsub__ = _e(OP.OP_SUB, inv=True)
    __rmul__ = _e(OP.OP_MUL, inv=True)
    __rdiv__ = _e(OP.OP_DIV, inv=True)
    __rand__ = _e(OP.OP_AND, inv=True)
    __ror__ = _e(OP.OP_OR, inv=True)
    __rxor__ = _e(OP.OP_XOR, inv=True)

    __eq__ = _e(OP.OP_EQ)
    __lt__ = _e(OP.OP_LT)
    __le__ = _e(OP.OP_LTE)
    __gt__ = _e(OP.OP_GT)
    __ge__ = _e(OP.OP_GTE)
    __ne__ = _e(OP.OP_NE)
    __rshift__ = _e(OP.OP_IN)
    __mod__ = _e(OP.OP_LIKE)


class Expr(Node):
    def __init__(self, lhs, op, rhs):
        super(Expr, self).__init__()
        self.lhs = lhs
        self.op = op
        self.rhs = rhs

    def clone(self):
        return Expr(self.lhs, self.op, self.rhs)


class FieldDescriptor(object):

    def __init__(self, field):
        self.field = field
        self.att_name = self.field.get_name()

    def __get__(self, instance, instance_type=None):
        if instance:
            return instance._data.get(self.att_name)
        return self.field

    def __set__(self, instance, value):
        value = self.field.validate(value)
        if self.att_name in instance._data:
            prev_val = instance._data[self.att_name]
            if self.field.multi:
                if isinstance(prev_val, list) or isinstance(prev_val, tuple):
                    prev_val = list(prev_val)
                else:
                    prev_val = [prev_val]
                prev_val.append(value)
            else:
                prev_val = value
            instance._data[self.att_name] = prev_val
        else:
            instance._data[self.att_name] = value


class Field(Node):

    def __init__(self, name='', multi=False, required=False, default=None):
        super(Field, self).__init__()
        self.name = name
        self.multi = multi
        self.required = required
        self.default = self.validate(default) if default else default

    def get_name(self):
        return self.name

    def set_name(self, name):
        self.name = name

    def validate(self, value):
        return value


class Integer(Field):

    def __init__(self, *args, **kwargs):
        super(Integer, self).__init__(*args, **kwargs)

    def validate(self, value):
        return int(value)


class Text(Field):

    def __init__(self, *args, **kwargs):
        super(Text, self).__init__(*args, **kwargs)

    def validate(self, value):
        return str(value)


class Float(Field):

    def __init__(self, *args, **kwargs):
        super(Float, self).__init__(*args, **kwargs)

    def validate(self, value):
        return float(value)


class Boolean(Field):

    def __init__(self, *args, **kwargs):
        super(Boolean, self).__init__(*args, **kwargs)

    def validate(self, value):
        if isinstance(value, string_types):
            value = value.lower()
            if value not in ("true", "false"):
                raise ValueError(u'ERROR: {} cannot convert to bool type'.format(value))
        elif isinstance(value, bool):
            value = str(value).lower()
        else:
            value = str(bool(value))
        return value


class Date(Field):

    def __init__(self, timezone=None, *args, **kwargs):
        self._timezone = timezone or dt_tz(timedelta(hours=8))
        if isinstance(self._timezone, string_types):
            self._timezone = tz.gettz(self._timezone)
        super(Date, self).__init__(*args, **kwargs)

    def validate(self, value):
        if isinstance(value, string_types):
            try:
                value = parser.parse(value)
            except Exception as e:
                raise ValueError('ERROR: Could not parse date from the value {}'.format(value), e)

        if isinstance(value, datetime):
            if self._timezone and value.tzinfo is None:
                value = value.replace(tzinfo=self._timezone)
        elif isinstance(value, date):
            value = self.validate(str(value))
        elif isinstance(value, int):
            value = datetime.utcfromtimestamp(value / 1000.0)
        else:
            raise ValueError('ERROR: Could not parse date from the value {}'.format(value))
        return datetime.strftime(value, '%Y-%m-%dT%H:%M:%S.%fZ')


class Object(Field):

    def __init__(self, *args, **kwargs):
        self._fields = {}
        for k, v in dict(kwargs).items():
            if isinstance(v, Field):
                v.set_name(k)
                setattr(self, k, v)
                self._fields[k] = v
                del kwargs[k]
        super(Object, self).__init__(*args, **kwargs)

    def set_name(self, name):
        super(Object, self).set_name(name)
        for k, v in self._fields.items():
            v.set_name('{}.{}'.format(name, k))

    def validate(self, value):
        if isinstance(value, dict):
            return self._validate_dict(value)
        elif isinstance(value, string_types):
            return self._validate_json(value)
        elif isinstance(value, object):
            return self._validate_object(value)
        else:
            raise ValueError(u'ERROR: unsupported value type {} for Object Field'.format(value))

    def _validate_dict(self, value_dict):
        validate_dict = {}
        for name, field in self._fields.items():
            if name in value_dict:
                validate_dict[name] = field.validate(value_dict[name])
            else:
                if field.default:
                    validate_dict[name] = field.default
        return validate_dict

    def _validate_json(self, value_json):
        try:
            value_dict = json.loads(value_json)
        except Exception as ex:
            value_dict = literal_eval(value_json)
        return self._validate_dict(value_dict)

    def _validate_object(self, value_object):
        if len(value_object.__dict__) > 1000:
            raise Exception(u'ERROR: too many field in parsed object {}'.format(value_object.__class__))
        return self._validate_dict(value_object.__dict__)
