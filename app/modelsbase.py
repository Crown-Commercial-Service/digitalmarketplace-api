import sqlalchemy
from sqlalchemy import String, Integer, Column
from sqlalchemy.ext.declarative import declarative_base, DeclarativeMeta, as_declarative, declared_attr
from flask_sqlalchemy import SQLAlchemy, Model, BaseQuery, declarative_base, _QueryProperty

import gc
import re
from collections import OrderedDict

from sqlalchemy.orm.exc import UnmappedClassError

import pendulum
import datetime

import json
from flask import url_for, request

from werkzeug.routing import BuildError
import six

from sqlalchemy.orm.relationships import RelationshipProperty

from collections import Mapping

import decimal
import uuid

from six import string_types
from collections import Iterable

from dmutils.data_tools import ValidationError


def normalize_key_case(d):
    if not isinstance(d, Mapping):
        return d
    d = d.copy()
    return {to_snake(k): normalize_key_case(v) for k, v in d.items()}


class CustomEncoder(json.JSONEncoder):
    def __init__(self, *args, **kwargs):
        kwargs['indent'] = 4
        kwargs['sort_keys'] = True
        super(CustomEncoder, self).__init__(*args, **kwargs)

    def default(self, obj):
        if hasattr(obj, 'serializable'):
            return obj.serializable
        if isinstance(obj, datetime.datetime):
            return pendulum.instance(obj).to_iso8601_string()
        if isinstance(obj, decimal.Decimal):
            return str(obj)
        return super(CustomEncoder, self).default(obj)


enc = CustomEncoder(indent=4, sort_keys=True)
jsondumps = enc.encode


def to_snake(s):
    return (s[0].lower() + re.sub(
        r'([A-Z])', lambda m: "_" + m.group(0).lower(), s[1:]))


def identity_link(name, id):
    def pluralize(word):
        if word == 'case_study':
            word = 'case_studies'
        elif word == 'address':
            word = 'addresses'
        elif not word.endswith('s'):
            return '{}s'.format(word)
        return word.replace('_', '-')

    if id is None:
        raise ValueError

    try:
        url_root = request.url_root
    except RuntimeError:
        url_root = '/'

    return url_root + '{}/{}'.format(pluralize(name), id)


DEFAULT_REPR_FIELDS = ['id', 'name', 'slug']


class ExcludedException(Exception):
    pass


@six.python_2_unicode_compatible
class MyModel(Model):
    def __str__(self):
        return repr(self)

    def __repr__(self):
        fields_for_repr = [
            _ for _ in DEFAULT_REPR_FIELDS if hasattr(self, _)
        ]

        try:
            fields_for_repr += self.ADDITIONAL_REPR_FIELDS
        except AttributeError:
            pass

        field_values = [
            '{}={}'.format(f, getattr(self, f))
            for f
            in fields_for_repr]

        return '<{}: {}>'.format(
            self.__class__.__name__,
            ', '.join(field_values)
        )

    @property
    def _name(self):
        name = type(self).__name__
        return (name[0].lower() + re.sub(
            r'([A-Z])', lambda m: "_" + m.group(0).lower(), name[1:]))

    def update_from_json_before(self, j):
        return j

    def update_from_json_after(self, j):
        return j

    def update_from_json(self, j):
        if isinstance(j, six.string_types):
            j = json.loads(j)

        j = self.update_from_json_before(j)

        fields = set(self._fields)
        relationships = set(self._relationships)
        props = set(self._props)
        incoming = set(j.keys())

        fields_to_update = incoming & fields
        relationships_to_update = incoming & relationships
        leftovers = incoming - props
        leftovers.discard('links')

        rc = self._relationship_classes

        for k in fields_to_update:
            setattr(self, k, j[k])

        for k in relationships_to_update:
            if '{}_id'.format(k) in fields_to_update:
                continue
            c = rc[k]
            subj = j[k]

            if isinstance(subj, Mapping):
                if all(_.isdigit() for _ in subj.keys()):
                    # {'0': {'a': 'b'}, '1': {'a': 'c'}}
                    items = [(int(i), v) for i, v in dict(subj).items()]
                    from_json = [c.from_json(v) for _, v in sorted(items)]
                else:
                    # {'a': 'b'}
                    from_json = c.from_json(subj)
            else:
                # [{'a': 'b'}, {'a': 'c'}]
                from_json = [c.from_json(_) for _ in subj]

            setattr(self, k, from_json)
        if hasattr(self, 'data'):
            leftover_dict = {k: j[k] for k in leftovers}

            try:
                self.data.update(leftover_dict)
            except AttributeError:
                self.data = leftover_dict
        elif leftovers:
            leftover_list = ', '.join(sorted(leftovers))
            raise ValidationError('unrecognized field(s): {}'.format(leftover_list))

        j = self.update_from_json_after(j)

    def url_for_entity(self, name):
        if name == self.api_entity_name:
            id_attr_name = 'id'
        else:
            id_attr_name = '{}_id'.format(name)

        route = 'main.get_{}_by_id'.format(name)
        param_name = '{}_id'.format(name)
        args = {param_name: getattr(self, id_attr_name)}
        return url_for(route, **args)

    @property
    def _relationship_classes(self):
        c = type(self)
        return {r: getattr(c, r).mapper.class_ for r in self._relationships}

    @property
    def _props(self):
        c = type(self)
        if not hasattr(c, '_propslist'):
            c._propslist = get_properties(c)
        return c._propslist

    @property
    def _fields(self):
        c = type(self)
        if not hasattr(c, '_fieldslist'):
            c._fieldslist = get_fields(c)
        return c._fieldslist

    @property
    def _relationships(self):
        c = type(self)
        if not hasattr(c, '_relationshipslist'):
            c._relationshipslist = get_relationships(c)
        return c._relationshipslist

    @property
    def _ordereddict(self):
        """
        Return this object's properties as an OrderedDict.
        """
        return OrderedDict(
            (each, getattr(self, each)) for each in self._props)

    @property
    def _dict(self):
        """
        Return this object's properties as a dictionary.
        """
        return {each: getattr(self, each) for each in self._props}

    @property
    def _fieldsdict(self):
        """
        Return this object's properties as a dictionary.
        """
        return {each: getattr(self, each) for each in self._fields}

    @property
    def serializable(self):
        return self._serializable()

    def get_serializable(self, only=None):
        only = only or [self._name]
        return self._serializable(only=[self._name])

    def _serializable(self, exclude=None, only=None, recurse=0):
        exclude = exclude or []
        exclude = list(exclude)

        if self._name in exclude:
            raise ExcludedException()

        if only is not None and self._name not in only:
            raise ExcludedException()

        exclude.append(self._name)

        try:
            data = self.data.copy()
        except AttributeError:
            data = {}

        data.update({k: v for k, v in self._fieldsdict.items() if k != 'data'})

        data['links'] = {}

        try:
            self.id
        except AttributeError:
            # return early as this is likely a many-to-many
            return data

        if self.id is not None:
            data['links']['self'] = identity_link(self._name, self.id)

        def get_related(x):
            if x is None:
                return None
            elif not isinstance(x, string_types) and isinstance(x, Iterable):
                return [_._serializable(exclude=exclude, only=only, recurse=recurse + 1) for _ in x]
            else:
                return x._serializable(exclude=exclude, only=only, recurse=recurse + 1)

        if len(exclude) != len(set(exclude)):
            print('duplicates in exclude!')
            raise ValueError

        for r in self._relationships:
            no_serialize = False
            try:
                if r in self.EXCLUDE_FOR_SERIALIZATION:
                    no_serialize = True
            except AttributeError:
                pass

            if not no_serialize:
                try:
                    data[r] = get_related(getattr(self, r))
                except ExcludedException:
                    pass

            fk_attr = '{}_id'.format(r)
            alternate_fk_id = '{}_code'.format(r)

            try:
                fk_id = getattr(self, fk_attr)
            except AttributeError:
                try:
                    fk_id = getattr(self, alternate_fk_id)
                except AttributeError:
                    continue

            if fk_id is not None:
                data['links'][r] = identity_link(r, fk_id)

        if 'created_at' in data:
            data['createdAt'] = data['created_at']

        data = self.serializable_after(data)
        return data

    def serializable_after(self, data):
        return data

    @property
    def json(self):
        return jsondumps(self.serializable)


class MySQLAlchemy(SQLAlchemy):
    def make_declarative_base(self, model_class, metadata=None):
        """Creates the declarative base."""
        base = declarative_base(cls=MyModel, name='Model',
                                metadata=metadata,
                                metaclass=DeclarativeMeta)
        base.query = _QueryProperty(self)
        return base


def find_subclasses(cls):
    all_refs = gc.get_referrers(cls)
    results = []
    for obj in all_refs:
        # __mro__ attributes are tuples
        # and if a tuple is found here, the given class is one of its members
        if (
                isinstance(obj, tuple) and
                # check if the found tuple is the __mro__ attribute of a class
                getattr(obj[0], "__mro__", None) is obj):
            results.append(obj[0])
    return results


def get_properties(_class):
    """
    Gets the mapped properties of this mapped object.
    """

    def _props():
        mapper = sqlalchemy.orm.class_mapper(_class)
        for prop in mapper.iterate_properties:
            yield prop.key

    return list(_props())


def get_fields(_class):
    """
    Gets the mapped properties of this mapped object.
    """

    def _props():
        mapper = sqlalchemy.orm.class_mapper(_class)
        for prop in mapper.iterate_properties:
            if not isinstance(prop, RelationshipProperty):
                yield prop.key

    return list(_props())


def get_relationships(_class):
    """
    Gets the mapped properties of this mapped object that represent relationships to other tables.
    """

    def _props():
        mapper = sqlalchemy.orm.class_mapper(_class)
        for prop in mapper.iterate_properties:
            if isinstance(prop, RelationshipProperty):
                yield prop.key

    return list(_props())
