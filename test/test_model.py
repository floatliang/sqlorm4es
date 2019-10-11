# -*- coding: utf-8 -*-
# @Time    : 2019/10/9 17:49
# @Author  : floatsliang
# @File    : test_model.py
from datalab.db.es.orm.model import BaseModel
from datalab.db.es.orm.field import Field, Integer, Text, Date, Boolean, Float, Object, FieldDescriptor


def test_generate_model():

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

    class LogCenterES(LogCenter):

        es_version = Float(default=6.2)

    LogCenter.ok = 1

    assert LogCenter.get_index() == 'lala'
    assert LogCenter.get_database() == {
            "host": "122.23.2.23"
        }
    assert not LogCenter._data
    assert len(LogCenter._fields) == 5
    for name, field in LogCenter._fields:
        assert isinstance(field, FieldDescriptor), 'Field not converted to descriptor'
        assert isinstance(getattr(LogCenter, name), Field)

    assert LogCenterES.get_index() == 'LogCenterES'
    assert LogCenterES.get_database() == {}
    assert len(LogCenterES._fields) == 6, 'Model inherit Field failed'


def test_instantiate_model():

    class SomeLog(BaseModel):

        log_name = Text(required=True, default='some_log')
        log_type = Object(
            source_id=Integer(default='22'),
            ok=Boolean(default='FALSE'),
            default={
                'source_id': 11,
                'ok': True
            }
        )

    assert SomeLog.get_index() == 'SomeLog'
    assert SomeLog.get_database() == {}
    assert SomeLog._data == {
        'log_name': 'some_log',
        'log_type': {
            'source_id': 11,
            'ok': 'true'
        }
    }
    new_log = SomeLog(multi=True, index='NotSomeLog', database={
        'host': '127.0.0.1'
    }, log_name='error_log', log_type={
        'source_id': 33,
        'ok': 'true'
    })
    assert new_log._data is not SomeLog._data
    assert new_log.get_index() != SomeLog.get_index()
    assert new_log.get_database() != SomeLog.get_database()
    assert new_log._data == {
        'log_name': 'error_log',
        'log_type': {
            'source_id': 33,
            'ok': 'true'
        }
    }


