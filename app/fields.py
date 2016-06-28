from sqlalchemy.ext.mutable import Mutable, MutableDict

# here we implement subclasses of json-style containers (dict, list) which advertize their mutations back to a parent
# model instance when used for e.g. a JSON field. this allows validators to run a *little* more reliably.

# the key to understanding the inheritance pattern used here is remembering that `coerce` only gets called at
# field assignment time. so the delegation of the `coerce` calls is designed around the desired behaviour when a
# json-style container object is assigned to a target field. we make DMMutableList and DMMutableDict inherit from
# DMMutableContainer so that, if they need to, a user is able to do an
# `isinstance(some_dmmutabledict, DMMutableContainer)` and get a sensible answer (True)


class DMMutableContainer(Mutable):
    """
        All this does is implement a common `coerce` method for initializing the appropriate implementation class, other
        than that it's an abstract class. The effect is that this class can be used to apply mutable container behaviour
        to fields that can accept either dicts or lists.
    """
    @classmethod
    def coerce(cls, key, value):
        "Convert plain json-like containers to their DMMutable* equivalents."
        if value is None:
            # it's not our job to filter out nulls here
            return None
        elif isinstance(value, DMMutableContainer):
            return value
        elif isinstance(value, dict):
            return DMMutableDict(value)
        elif isinstance(value, (tuple, list,)):
            return DMMutableList(value)

        # this call will raise ValueError
        return super(cls).coerce(key, value)


class DMMutableDict(DMMutableContainer, MutableDict):
    @classmethod
    def coerce(cls, key, value):
        # A strict coerce method used for restricting a target field to containing dicts
        if value is None:
            # it's not our job to filter out nulls here
            return None
        elif isinstance(value, DMMutableDict):
            return value
        elif isinstance(value, dict):
            return DMMutableDict(value)

        # deliberately *not* delegating this call via super() as our parent class will be too lenient in its coerce
        # implementation
        msg = "Attribute '%s' does not accept objects of type %s"
        raise ValueError(msg % (key, type(value)))


class DMMutableList(DMMutableContainer, list):
    @classmethod
    def coerce(cls, key, value):
        # A strict coerce method used for restricting a target field to containing lists/tuples
        if value is None:
            # it's not our job to filter out nulls here
            return None
        elif isinstance(value, DMMutableList):
            return value
        elif isinstance(value, (tuple, list,)):
            return DMMutableList(value)

        # deliberately *not* delegating this call via super() as our parent class will be too lenient in its coerce
        # implementation
        msg = "Attribute '%s' does not accept objects of type %s"
        raise ValueError(msg % (key, type(value)))

    #
    # catch all mutating methods of list and make sure they advertize the change
    #

    def __setitem__(self, *args, **kwargs):
        r = super(DMMutableList, self).__setitem__(*args, **kwargs)
        self.changed()
        return r

    def __delitem__(self, *args, **kwargs):
        r = super(DMMutableList, self).__delitem__(*args, **kwargs)
        self.changed()
        return r

    def __setslice__(self, *args, **kwargs):
        # apparently though this method is deprecated since python 2.0 we still have to implement it as the cpython
        # builtin types implement it
        r = super(DMMutableList, self).__setslice__(*args, **kwargs)
        self.changed()
        return r

    def __delslice__(self, *args, **kwargs):
        r = super(DMMutableList, self).__delslice__(*args, **kwargs)
        self.changed()
        return r

    def __iadd__(self, *args, **kwargs):
        r = super(DMMutableList, self).__iadd__(*args, **kwargs)
        self.changed()
        return r

    def __imul__(self, *args, **kwargs):
        r = super(DMMutableList, self).__imul__(*args, **kwargs)
        self.changed()
        return r

    def append(self, *args, **kwargs):
        r = super(DMMutableList, self).append(*args, **kwargs)
        self.changed()
        return r

    def extend(self, *args, **kwargs):
        r = super(DMMutableList, self).extend(*args, **kwargs)
        self.changed()
        return r

    def insert(self, *args, **kwargs):
        r = super(DMMutableList, self).insert(*args, **kwargs)
        self.changed()
        return r

    def pop(self, *args, **kwargs):
        r = super(DMMutableList, self).pop(*args, **kwargs)
        self.changed()
        return r

    def reverse(self, *args, **kwargs):
        r = super(DMMutableList, self).reverse(*args, **kwargs)
        self.changed()
        return r

    def sort(self, *args, **kwargs):
        r = super(DMMutableList, self).sort(*args, **kwargs)
        self.changed()
        return r
