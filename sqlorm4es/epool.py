# -*- coding: utf-8 -*-
# @Time    : 2019/9/9 9:47
# @Author  : floatsliang
# @File    : epool.py
import json
import random
from threading import Lock
from timeit import default_timer

from elasticsearch import Elasticsearch, ImproperlyConfigured

_DEFAULT_CONF = {
    'hosts': ['127.0.0.1:9200'],
    'maxsize': 20,
    'sniff_on_start': False,
    'sniff_on_connection_fail': False,
    'sniff_timeout': .1,
    'sniffer_timeout': None,
    'retry_on_timeout': False,
    'timeout': 60,
}

_DEFAULT_TIMEOUT = 600
_MAX_CONN = 10
_CLEAN_RATIO = 0.2
_OVERLOAD_RATIO = 2
_MAX_CLEAN = 10


class ESConnection(Elasticsearch):
    _version = 6.8

    def __init__(self, config, timeout):
        self._timeout = timeout
        self._version = config.get("es_version", self._version)
        super(ESConnection, self).__init__(**config)

    @property
    def version(self):
        return self._version

    @property
    def timeout(self):
        return self._timeout

    def set_timeout(self, timeout):
        self._timeout = timeout


class DBPool(object):

    def __init__(self, engine=None, clean_timeout=True,
                 pool_timeout=_DEFAULT_TIMEOUT, max_conn=_MAX_CONN, **conf):
        conf = conf or _DEFAULT_CONF
        self._default_connect = ESConnection(conf, None)
        self._key = json.dumps(tuple(sorted(conf.items())))
        self._pool = {}
        self._clean_timeout = clean_timeout
        self._timeout = pool_timeout
        self._max_conn = max_conn
        self._clean_conn_per_round = min(int(max_conn * _CLEAN_RATIO), _MAX_CLEAN)
        self._max_overload_conn = max_conn * _OVERLOAD_RATIO
        self._clean_lock = Lock()

    @staticmethod
    def _is_conn_timeout(conn):
        return True if default_timer() > conn.timeout else False

    def _new_conn(self, key, timeout, config):
        now = default_timer()
        try:
            conn = ESConnection(config, now + timeout)
        except Exception as ex:
            if isinstance(ex, ImproperlyConfigured):
                raise Exception(u'ERROR: Config passed to the client is inconsistent or invalid')
            raise Exception(u'ERROR: {}'.format(str(ex)))

        if len(self._pool) < self._max_overload_conn:
            self._pool[key] = conn
        return conn

    def _get_conn(self, key, timeout, config):
        conn = self._pool.get(key, None)

        if conn:
            if DBPool._is_conn_timeout(conn):
                conn.set_timeout(default_timer() + timeout)
            return conn
        else:
            return self._new_conn(key, timeout, config)

    def _clean_timeout_conn(self):
        if len(self._pool) > self._max_conn:
            if self._clean_lock.acquire(blocking=False):
                clean_list = random.choices(list(self._pool.keys()),
                                            k=self._clean_conn_per_round)
                for key in clean_list:
                    if DBPool._is_conn_timeout(self._pool[key]):
                        del self._pool[key]

                self._clean_lock.release()

    def connect(self, pool_timeout=None, **config):
        if self._clean_timeout:
            self._clean_timeout_conn()

        if not config:
            return self._default_connect
        key = json.dumps(tuple(sorted(config.items())))
        if key == self._key:
            return self._default_connect

        pool_timeout = pool_timeout or self._timeout
        conn = self._get_conn(key, pool_timeout, config)

        return conn


POOL = DBPool()
