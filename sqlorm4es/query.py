# -*- coding: utf-8 -*-
# @Time    : 2019/9/11 15:31
# @Author  : floatsliang
# @File    : utils.py
import sys
import copy
import logging
import inspect
import re
import datetime


__all__ = ['Q', 'Match', 'Term', 'Terms', 'Range', 'Sort', 'Aggs', 'Highlight', 'Bool', 'Dsl']
logger = logging.getLogger(__name__)


class InvalidVersionError(Exception):
    pass


def _not_allowed(clazz, field_name):
    def inner(*args, **kwargs):
        pass

    if hasattr(clazz, 'with_' + field_name):
        setattr(clazz, 'with_' + field_name, inner)
    if hasattr(clazz, 'get_' + field_name):
        setattr(clazz, 'get_' + field_name, inner)


def _get_banned_field_list(clazz, version):
    banned_field_list = []
    if version < 7:
        banned_field_list += clazz.get('_NOT_ALLOWED_7X', [])
    if version < 6:
        banned_field_list += clazz.get('_NOT_ALLOWED_6X', [])
    return banned_field_list


def Q(name_or_query=None, *args, **kwargs):
    if isinstance(name_or_query, Base):
        return name_or_query
    if isinstance(name_or_query, dict):
        if len(name_or_query) != 1:
            raise ValueError(u'ERROR: dict type name_or_query length should be 1')
        clazz_name, params = name_or_query.popitem()
        kwargs['q'] = params
    elif name_or_query.lower() in _clazz_dict:
        clazz_name = name_or_query.lower()
    else:
        raise NotImplementedError(u'ERROR: {} leaf field is not implemented yet'.format(name_or_query))
    return _clazz_dict[clazz_name](*args, **kwargs)


class Base(dict):
    _func_dict = {}

    def __init__(self, version=5.1, *args, **kwargs):
        super(Base, self).__init__()
        version = float(version)
        banned_field_list = _get_banned_field_list(self, version)
        for field_name in banned_field_list:
            _not_allowed(self, field_name)
        for k, v in inspect.getmembers(self, inspect.ismethod):
            if k.startswith('with_'):
                self._func_dict[k] = v

        self._with_given_fields(*args, **kwargs)

    def __getattr__(self, field):
        actual_field = 'with_' + field
        return super(Base, self).__getattribute__(actual_field)

    def _with_given_fields(self, *args, **kwargs):
        for k, v in kwargs.items():
            k = 'with_{}'.format(k.lower())
            if k in self._func_dict:
                self._func_dict[k](v)

    def _validate_query_field(self, query: dict, copied=False):
        clazz_name = self.__class__.__name__.lower()
        if len(query) == 1 and query.get(clazz_name, None):
            query = query[clazz_name]
        return copy.deepcopy(query) if copied else query

    def _get_and_set(self, field, default):
        got = self.get(field, default)
        self._work_dir[field] = got
        return got


class Term(Base):

    def __init__(self, q: dict = None, *args, **kwargs):
        if q:
            query = self._validate_query_field(q, kwargs.get('copied', False))
            if len(query) == 1:
                field, params = query.popitem()
                kwargs = params
            else:
                raise ValueError(u'ERROR: {} can only have one field'.format(self.__class__))
        else:
            field = kwargs.get('field', None)
            if not field:
                raise AttributeError(u'ERROR: {} field cannot be empty'.format(self.__class__))
        self['term'] = {
            field: {}
        }
        self._work_dir = self['term'][field]
        super(Term, self).__init__(*args, **kwargs)

    def with_value(self, value):
        self._work_dir['value'] = value
        return self

    def with_boost(self, boost: float = 1.0):
        boost = float(boost)
        self._work_dir['boost'] = boost
        return self


class Terms(Base):

    def __init__(self, q: dict = None, *args, **kwargs):
        if q:
            kwargs = q
        else:
            self.field = kwargs.pop('field')
        self['terms'] = {}
        self._work_dir = self['terms']
        self._work_dir.update(kwargs)
        super(Base, self).__init__()

    def with_value(self, values, field=None):
        if not field:
            self._work_dir[self.field] = values
        else:
            self._work_dir[field] = values
        return self

    def with_boost(self, boost=1.0):
        boost = float(boost)
        self._work_dir['boost'] = boost
        return self


class Match(Base):

    def __init__(self, q: dict = None, *args, **kwargs):
        if q:
            query = self._validate_query_field(q, kwargs.get('copied', False))
            if len(query) == 1:
                field, params = query.popitem()
                kwargs = params
            else:
                raise ValueError(u'ERROR: {} can only have one field'.format(self.__class__))
        else:
            field = kwargs.get('field', None)
            if not field:
                raise AttributeError(u'ERROR: {} field cannot be empty'.format(self.__class__))
        self['match'] = {
            field: {}
        }
        self._work_dir = self['match'][field]
        super(Match, self).__init__(*args, **kwargs)

    def with_query(self, query):
        self._work_dir['query'] = query
        return self

    def with_analyzer(self, analyzer: str = "standard"):
        analyzer = '{}'.format(analyzer)
        self._work_dir['analyzer'] = analyzer
        return self

    def with_fuzziness(self, fuzziness: str = "1,"):
        fuzziness = '{}'.format(fuzziness)
        self._work_dir['fuzziness'] = fuzziness
        return self

    def with_operator(self, operator: str = "and"):
        operator = '{}'.format(operator)
        self._work_dir['operator'] = operator
        return self

    def with_zero_term_query(self, zero_term_query: str = "all"):
        zero_term_query = '{}'.format(zero_term_query)
        self._work_dir['zero_term_query'] = zero_term_query
        return self

    def with_cutoff_frequency(self, cutoff_frequency: float = 0.001):
        cutoff_frequency = float(cutoff_frequency)
        self._work_dir['cutoff_frequency'] = cutoff_frequency
        return self


class Range(Base):

    def __init__(self, q: dict = None, *args, **kwargs):
        if q:
            query = self._validate_query_field(q, kwargs.get('copied', False))
            if len(query) == 1:
                field, params = query.popitem()
                kwargs = params
            else:
                raise ValueError(u'ERROR: {} can only have one field'.format(self.__class__))
        else:
            field = kwargs.get('field', None)
            if not field:
                raise AttributeError(u'ERROR: {} field cannot be empty'.format(self.__class__))
        self['range'] = {
            field: {}
        }
        self._work_dir = self['range'][field]
        super(Range, self).__init__(*args, **kwargs)

    def with_gte(self, gte: str):
        if gte:
            self._work_dir['gte'] = '{}'.format(gte)
        return self

    def with_lte(self, lte: str):
        if lte:
            self._work_dir['lte'] = '{}'.format(lte)
        return self

    def with_gt(self, gt: str):
        if gt:
            self._work_dir['gt'] = '{}'.format(gt)
        return self

    def with_lt(self, lt: str):
        if lt:
            self._work_dir['lt'] = '{}'.format(lt)
        return self

    def with_boost(self, boost: str):
        if boost:
            self._work_dir['boost'] = '{}'.format(boost)
        return self

    def with_format(self, formats: str = "dd/MM/yyyy||yyyy"):
        if formats:
            self._work_dir['format'] = '{}'.format(formats)
        return self

    def with_time_zone(self, time_zone: str = "+08:00"):
        if time_zone:
            self._work_dir['time_zone'] = '{}'.format(time_zone)
        return self


class Sort(Base):

    def __init__(self, q: dict = None, *args, **kwargs):
        if q:
            query = self._validate_query_field(q, kwargs.get('copied', False))
            if len(query) == 1:
                field, params = query.popitem()
                kwargs = params
            else:
                raise ValueError(u'ERROR: {} can only have one field'.format(self.__class__))
        else:
            field = kwargs.get('field', None)
            if not field:
                raise AttributeError(u'ERROR: {} field cannot be empty'.format(self.__class__))
        self[field] = {}
        self._work_dir = self[field]
        super(Sort, self).__init__(*args, **kwargs)

    def with_order(self, order: str = "asc"):
        self._work_dir['order'] = order
        return self

    def with_mode(self, mode: str):
        self._work_dir['mode'] = str(mode)
        return self

    def with_unit(self, unit: str):
        self._work_dir['unit'] = str(unit)
        return self

    def with_nested_path(self, nested_path: str):
        self._work_dir['nested_path'] = str(nested_path)
        return self

    def with_nested_filter(self, nested_filter: str):
        self._work_dir['nested_filter'] = str(nested_filter)
        return self


class Aggs(Base):

    def __init__(self, q: dict = None, *args, **kwargs):
        if q:
            kwargs = q
        self._work_dir = self
        super(Base, self).__init__(*args, **kwargs)

    def terms(self, field, name='', order_by='_count', order='asc'):
        if not name:
            name = "group_by_{}".format(field)
        self._work_dir[name] = {
            "terms": {
                "field": field,
                "order": {order_by: order}
            }
        }
        return self

    def metrics(self, field, name='', op='max'):
        if op is 'count':
            return self
        if not name:
            name = "{}_{}".format(op, field)
        self._work_dir[name] = {
            op: {
                "field": field
            }
        }
        return self

    def aggs(self, query, name):
        name = "group_by_" + name
        self._work_dir[name]['aggs'] = query
        return self


class Highlight(Base):

    def __init__(self, q: dict = None, *args, **kwargs):
        if q:
            query = self._validate_query_field(q, kwargs.get('copied', False))
            kwargs = query
        self._work_dir = self
        super(Highlight, self).__init__(*args, **kwargs)

    def with_pre_tags(self, tag="<tag1>"):
        if not isinstance(tag, list):
            tag = [tag]
        pre_tags_list = self.get_pre_tags()
        pre_tags_list += tag
        return self

    def with_post_tags(self, tag="</tag1>"):
        if not isinstance(tag, list):
            tag = [tag]
        post_tags_list = self.get_post_tags()
        post_tags_list += tag
        return self

    def with_fields(self, field):
        self._work_dir['fields'] = field
        return self

    def with_order(self, order: str):
        self._work_dir['order'] = '{}'.format(order)
        return self

    def get_pre_tags(self):
        return self._get_and_set('pre_tags', [])

    def get_post_tags(self):
        return self._get_and_set('post_tags', [])


class Bool(Base):
    _FORMAL_DATE_PATTERN = re.compile(r'^(?P<year>\d{4})\D(?P<month>\d{2})\D(?P<day>\d{2}).*$')
    _NOW_DATE_PATTERN = re.compile(r'^now((?P<op>[-+])(?P<num>\d+)(?P<unit>([yMwdhHms])))?\s*$')

    def __init__(self, q: dict = None, *args, **kwargs):
        self._debug = kwargs.get('debug', False)
        scoring = kwargs.get('scoring', False)
        if q:
            kwargs = self._validate_query_field(q, kwargs.get('copied', True))
        self['bool'] = {}
        if scoring:
            self['bool']['filter'] = {
                'bool': {}
            }
            self._work_dir = self['bool']['filter']['bool']
        else:
            self._work_dir = self['bool']
        super(Bool, self).__init__(*args, **kwargs)

    def _go_to(self, term, path='filter'):
        path = '{}'.format(path).lower()
        if path == 'filter':
            self.with_filter(term)
        elif path == 'must':
            self.with_must(term)
        elif path == 'must_not':
            self.with_must_not(term)
        elif path == 'should':
            self.with_should(term)
        else:
            if self._debug:
                logger.debug(u'DEBUG: {} has been discard'
                             u' when going to {}'.format(term.__class__, path))
            else:
                raise NotImplementedError(u'ERROR: {} field not supported yet'.format(path))

    @classmethod
    def parse_date(cls, date_str: str):
        match_date = cls._FORMAL_DATE_PATTERN.match(date_str)
        if not match_date:
            match_date = cls._NOW_DATE_PATTERN.match(date_str)
            if not match_date:
                return None
            match_dict = match_date.groupdict()
            if not match_dict['op']:
                return datetime.date.today()
            diff_days = 0
            if match_dict['unit'] == 'y':
                diff_days = 365
            elif match_dict['unit'] == 'M':
                diff_days = 30
            elif match_dict['unit'] == 'w':
                diff_days = 7
            elif match_dict['unit'] == 'd':
                diff_days = 1
            if match_dict['op'] == '+':
                parsed_date = datetime.date.today() + datetime.timedelta(days=diff_days * int(match_dict['num']))
            else:
                parsed_date = datetime.date.today() + datetime.timedelta(days=-diff_days * int(match_dict['num']))
        else:
            match_dict = match_date.groupdict()
            parsed_date = datetime.date(int(match_dict['year']), int(match_dict['month']), int(match_dict['day']))
        return parsed_date

    def with_filter(self, args: [dict]):
        self._work_dir['filter'] = self._work_dir.get('filter', [])
        filter_list = self._work_dir['filter']
        if not isinstance(args, list) and not isinstance(args, tuple):
            args = [args]
        for query in args:
            if isinstance(query, dict):
                filter_list.append(Q(query))
            else:
                if self._debug:
                    logger.debug(u'DEBUG: {} has been discard'.format(query.__class__))
                else:
                    raise ValueError(u'ERROR: Term appended to [filter] '
                                     u'field must be subclass of dict')
        return self

    def with_must(self, args: [dict]):
        self._work_dir['must'] = self._work_dir.get('must', [])
        must_list = self._work_dir['must']
        if not isinstance(args, list) and not isinstance(args, tuple):
            args = [args]
        for query in args:
            if isinstance(query, dict):
                must_list.append(Q(query))
            else:
                if self._debug:
                    logger.debug(u'DEBUG: {} has been discard'.format(query.__class__))
                else:
                    raise ValueError(u'ERROR: Term appended to [must] '
                                     u'field must be subclass of dict')
        return self

    def with_must_not(self, args: [dict]):
        self._work_dir['must_not'] = self._work_dir.get('must_not', [])
        must_not_list = self._work_dir['must_not']
        if not isinstance(args, list) and not isinstance(args, tuple):
            args = [args]
        for query in args:
            if isinstance(query, dict):
                must_not_list.append(Q(query))
            else:
                if self._debug:
                    logger.debug(u'DEBUG: {} has been discard'.format(query.__class__))
                else:
                    raise ValueError(u'ERROR: Term appended to [must_not] '
                                     u'field must be subclass of dict')
        return self

    def with_should(self, args: [dict]):
        self._work_dir['should'] = self._work_dir.get('should', [])
        should_list = self._work_dir['should']
        if not isinstance(args, list) and not isinstance(args, tuple):
            args = [args]
        for query in args:
            if isinstance(query, dict):
                should_list.append(Q(query))
            else:
                if self._debug:
                    logger.debug(u'DEBUG: {} has been discard'.format(query.__class__))
                else:
                    raise ValueError(u'ERROR: Term appended to [should] '
                                     u'field must be subclass of dict')
        return self

    def with_minimum_should_match(self, match_num: float = 1, overwrite=False):
        if not overwrite and hasattr(self._work_dir, 'minimum_should_match'):
            return self

        if isinstance(match_num, str):
            self._work_dir['minimum_should_match'] = match_num
            return self

        match_num = float(match_num)
        if match_num == 0:
            match_num = "1"
        if -1 < match_num < 1:
            match_num = "{}%".format(match_num * 100)
        else:
            match_num = "{}".format(match_num)
        self._work_dir['minimum_should_match'] = match_num
        return self

    def with_start_time(self, ts_key: str = "@timestamp", start_time: str = "now-10d"):
        if start_time is None:
            start_time = "now-10d"
        self.with_range(field=ts_key, gte=start_time)
        return self

    def with_end_time(self, ts_key="@timestamp", end_time="now"):
        if end_time is None:
            end_time = "now"
        self.with_range(field=ts_key, lte=end_time)
        return self

    def with_term(self, field, value, go_to="filter", *args, **kwargs):
        if not field or not value:
            raise ValueError(u'ERROR: Field and value of term cannot be empty')
        term = Q(field=field, value=value, name_or_query='term', *args, **kwargs)
        self._go_to(term, go_to)
        return self

    def with_match(self, field, value, go_to='filter', *args, **kwargs):
        if not field or not value:
            raise ValueError(u'ERROR: Field and value of match cannot be empty')
        match = Q(field=field, value=value, name_or_query='match', *args, **kwargs)
        self._go_to(match, go_to)
        return self

    def with_range(self, field, go_to='filter', *args, **kwargs):
        if not field:
            raise ValueError(u'ERROR: Field of range cannot be empty')
        es_range = Q(field=field, name_or_query='range', *args, **kwargs)
        self._go_to(es_range, go_to)
        return self

    def get_filter(self):
        return self._get_and_set('filter', [])

    def get_must(self):
        return self._get_and_set('must', [])

    def get_must_not(self):
        return self._get_and_set('must_not', [])

    def get_should(self):
        return self._get_and_set('should', [])

    def get_time_range_list(self, ts_key="@timestamp"):
        filter_list = self.get_filter()
        time_range_list = []
        for field in filter_list:
            if 'range' in field and ts_key in field['range']:
                time_range_list.append(field)
        return time_range_list

    def get_time_scope(self, ts_key="@timestamp"):
        start_time = datetime.date(1001, 1, 1)
        end_time = datetime.date(9999, 1, 1)
        actual_end_time, actual_start_time = "", ""
        time_range_list = self.get_time_range_list(ts_key)
        for time_range in time_range_list:
            for op in time_range['range'][ts_key].keys():
                if op in ('gt', 'gte'):
                    cmped_date = Bool.parse_date(time_range['range'][ts_key][op])
                    if cmped_date is None:
                        pass
                    elif start_time < cmped_date:
                        start_time = cmped_date
                        actual_start_time = time_range['range'][ts_key][op]
                elif op in ('lt', 'lte'):
                    cmped_date = Bool.parse_date(time_range['range'][ts_key][op])
                    if cmped_date is None:
                        pass
                    elif end_time > cmped_date:
                        end_time = cmped_date
                        actual_end_time = time_range['range'][ts_key][op]

        return actual_start_time, actual_end_time


class Dsl(Base):
    _NOT_ALLOWED_6X = {'collapse', }
    _NOT_ALLOWED_7X = {'seq_no_primary_term', 'track_total_hits'}

    def __init__(self, q: dict = None, *args, **kwargs):
        version = float(kwargs.get('version', 5.1))
        self.debug = bool(kwargs.get('debug', False))
        scoring = kwargs.get('scoring', False)
        if version < 5 or version >= 8:
            raise InvalidVersionError(u'ERROR: ES version {} not supported'.format(version))

        if q:
            kwargs = self._validate_query_field(q, copied=True)
        kwargs['scoring'] = scoring
        kwargs['copied'] = False
        if 'from' in kwargs:
            kwargs['offset'] = kwargs['from']
            del kwargs['from']
        self._work_dir = self
        super(Dsl, self).__init__(*args, **kwargs)

    def with__source(self, ask_fields: list):
        include_list = self.get_source()
        if isinstance(ask_fields, dict):
            if 'includes' in ask_fields:
                ask_fields = ask_fields['includes']
            else:
                raise ValueError(u'ERROR: _source dict should have includes field')
        if not isinstance(ask_fields, list):
            ask_fields = [ask_fields]
        include_list += ask_fields
        return self

    def with_offset(self, offset="0", overwrite=False):
        if overwrite or 'from' not in self:
            self._work_dir['from'] = offset
        return self

    def with_size(self, size="10", overwrite=False):
        if overwrite or 'size' not in self:
            self._work_dir['size'] = size
        return self

    def with_query(self, query: dict, overwrite=False):
        if overwrite or 'query' not in self:
            query = Q(query)
            self._work_dir['query'] = query
        return self

    def with_sort(self, fields: list):
        sort_list = self.get_sort()
        if not isinstance(fields, list) and not isinstance(fields, tuple):
            fields = [fields]
        fields = [Q(q) for q in fields]
        sort_list += fields
        return self

    def with_aggs(self, query, name=''):
        self._work_dir['aggs'] = query
        return self

    def with_stored_fields(self, field: list):
        stored_fields_list = self.get_stored_fields()
        if not isinstance(field, list):
            field = [field]
        stored_fields_list += field
        return self

    def with_docvalue_fields(self, field: list):
        docvalue_fields_list = self.get_docvalue_fields()
        if not isinstance(field, list):
            field = [field]
        docvalue_fields_list += field
        return self

    def with_highlight(self, query: dict = None, *args, **kwargs):
        if kwargs.get('overwrite', False) or 'highlight' not in self:
            if query:
                query = Q(query)
            else:
                query = Q(name_or_query='highlight', *args, **kwargs)
            self._work_dir['highlight'] = query
        return self

    def with_explain(self, explain="true", overwrite=False):
        if overwrite or 'explain' not in self:
            self._work_dir['explain'] = explain
        return self

    def with_version(self, version="true", overwrite=False):
        if overwrite or 'version' not in self:
            self._work_dir['version'] = version
        return self

    def with_search_after(self, search_after):
        search_after_list = self.get_search_after()
        if not isinstance(search_after, list):
            search_after = [search_after]
        search_after_list += search_after
        return self

    def get_source(self):
        include_list = self.get('_source', [])
        if include_list:
            if isinstance(include_list, dict):
                include_list = include_list.get('includes', [])
            else:
                include_list = list(include_list)
            self._work_dir['_source']['includes'] = include_list
        else:
            self._work_dir['_source'] = {
                "includes": include_list
            }

        return include_list

    def get_sort(self):
        return self._get_and_set('sort', [])

    def get_size(self):
        return str(self._get_and_set('size', '10'))

    def get_from(self):
        return str(self._get_and_set('from', '0'))

    def get_query(self):
        return self._get_and_set('query', Q(name_or_query='bool'))

    def get_stored_fields(self):
        return self._get_and_set('stored_fields', [])

    def get_docvalue_fields(self):
        return self._get_and_set('docvalue_fields', [])

    def get_explain(self):
        return self._get_and_set('explain', 'false')

    def get_version(self):
        return self._get_and_set('version', 'true')

    def get_search_after(self):
        return self._get_and_set('search_after', [])


_clazz_dict = {k.lower(): v for k, v in inspect.getmembers(sys.modules[__name__], inspect.isclass)}