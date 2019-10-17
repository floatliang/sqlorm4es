### sqlorm4es

A simple and expressive (like peewee) sql-like orm for elasticsearch.

#### Examples

* Defining index model in a Django way:

```python
from sqlorm4es import *

class LogCenter(BaseModel):
    __index__ = 'lala'
    __database__ = {
        "host": "127.0.0.1:9200"
    }

    ok = Boolean(default=True)
    lineno = Integer(required=True)
    message = Text(default='xixi')
    timestamp = Date(name="@timestamp", timezone="+8")
    bigbrother = Object(
        head=Text(),
        hand=Object(
            finger=Float(),
            nail=Boolean()
        )
    )
```

* Search elasticsearch in a expressive way:

```python
res = LogCenter.select(LogCenter.ok, LogCenter.lineno, 'max(lineno)') \
    .where(((LogCenter.ok == False) & (LogCenter.message != 'error')) |
           (LogCenter.timestamp >= '2017-10-12') |
           (LogCenter.bigbrother.head >> ' ( tough; soft, medium soft ) '))\
    .execute()
```

* Note that and(&)/or(|) expression in where can be nested
* Also support group by aggregation: MAX, MIN, AVG, SUM, COUNT...
* Also support order by, LIMIT, OFFSET:

```python
res = LogCenter.select('max(lineno)')\
    .group_by(LogCenter.ok, LogCenter.timestamp)\
    .order_by((LogCenter.timestamp, 'asc'))\
    .execute()
```
* Manipulate document like a normal python object, value will be validated when assigning it (eg. value in Date Field all stored as UTC):
```python
new_log = LogCenter(ok=False, message='oops', timestamp='2019-10-10')
new_log.bigbrother = {
    "head": 'tough',
    "hand": {
        "finger": "long",
        "nail": "clean"
    }
}
```
* Create a single document:
```python
new_log.save()
```
* **Insert, Delete, Update and Index operation**: Coming soon...

#### Install
Sqlorm4es has been packaged to pypi, so just need one simple command to install it:
```shell
pip install sqlorm4es
```

#### Elasticsearch driver
Sqlorm4es implemented a simple almost lock-free connection pool based on official Elasticsearch client. As it is lock-free, so i am not sure whether it is thread-safe, but it works fine under my own multi-thread tests :)
* Note that if you did not set config of your model, it will use the default config as below:
```python
config = {
    'hosts': ['127.0.0.1:9200'],
    'maxsize': 20,
    'sniff_on_start': False,
    'sniff_on_connection_fail': False,
    'sniff_timeout': .1,
    'sniffer_timeout': None,
    'retry_on_timeout': False,
    'timeout': 60,
}
```