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
from flask import url_for


class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'serializable'):
            return obj.serializable
        if isinstance(obj, datetime.datetime):
            return pendulum.instance(obj).to_iso8601_string(extended=True)

        return super(CustomEncoder, self).default(obj)
enc = CustomEncoder(indent=4, sort_keys=True)


class MyModel(Model):
    @property
    def api_entity_name(self):
        name = type(self).__name__
        return (name[0].lower() + re.sub(
            r'([A-Z])', lambda m: "_" + m.group(0).lower(), name[1:]))

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
    def _props(self):
        c = type(self)
        if not hasattr(c, '_propertieslist'):
            c._propertieslist = get_properties(c)
        return c._propertieslist

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
    def serializable(self):
        if hasattr(self, 'data'):
            data = self.data.copy()
        else:
            data = {}
        data.update(self._dict)

        data['links'] = {}
        data['links']['self'] = self.url_for_entity(self.api_entity_name)

        if hasattr(self, 'user'):
            data['links']['user'] = self.url_for_entity('user')

        if 'created_at' in data:
            data['createdAt'] = data['created_at']

        return data

    @property
    def json(self):
        return enc.encode(self.serializable)


class MySQLAlchemy(SQLAlchemy):
    def make_declarative_base(self, metadata=None):
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
