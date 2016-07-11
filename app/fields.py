import threading
from collections import deque

from sqlalchemy.ext.mutable import Mutable, MutableDict
from sqlalchemy.orm.attributes import set_attribute
from sqlalchemy.util import memoized_property

from six import iteritems

from .utils import WeakIdentitySet

# here we implement subclasses of json-style containers (dict, list) which advertize their mutations back to a parent
# model instance when used for e.g. a JSON field. this allows validators to run a *little* more reliably, though more
# importantly, a model instance which has had its json changed but hasn't received a flag_modified will not attempt
# to save the json back on session commit, meaning some updates could get lost.


class SetTriggeringMutable(Mutable):
    """
    A Mutable subclass which emits history events through `set_attribute` on `change()` which should have the
    effect of causing validators to be run
    """
    def changed(self):
        # we specifically have to let the parent class trigger its flag_modified *before* we trigger
        # set_attribute - i'm sure why - the details of this seem to lurk deep in the internals of sqlalchemy
        r = super(SetTriggeringMutable, self).changed()
        # iterating through a copy of the items because the set_attribute will possibly alter the _parents
        # WeakKeyDictionary (we're not worried that our snapshot could be stale...)
        for parent, key in tuple(iteritems(self._parents)):
            set_attribute(parent, key, getattr(parent, key))
        return r


class _ThreadLocal(threading.local):
    # we need a global, but thread-local, record of activations of the changed() method to prevent recursion-loops in
    # objects that have somehow become self-parented.
    def __init__(self):
        # a deque of DMMutableContainer objects whose .changed() methods we are currently "inside". used like a stack.
        self.changed_activations = deque()


class DMMutableContainer(SetTriggeringMutable):
    """
        Abstract class defining methods that support "mutable container" behaviour.
    """
    _thread_local = _ThreadLocal()

    @memoized_property
    def _container_parents(self):
        """
            memoized_property a la `Mutable._parents` implementation.

            Set of parents that contain us. These should all be DMMutableContainer instances. Kept as a set as we're
            not interested in which key/index we're under as it can change in ways that are a pain to track e.g. in the
            case of lists that get items inserted at positions other than the end.
        """
        return WeakIdentitySet()

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

    def coerce_contained(self, value):
        """
            Common implementation of routine we have to go through for an item which is about to become "contained"
            by us
        """
        if isinstance(value, DMMutableContainer):
            mc = value
        if isinstance(value, dict):
            mc = DMMutableDict(value)
        elif isinstance(value, (list, tuple,)):
            mc = DMMutableList(value)
        else:
            # all other json-able objects are immutable in python
            return value

        # we've got to make sure any contained DMMutableContainers know their mutations affect *us* now
        mc._container_parents.add(self)
        return mc

    def changed(self):
        # first, check we aren't already inside a changed() call to this object
        if self in self._thread_local.changed_activations:
            # oh dear. looks like a circular reference. prevent infinite recursion.
            return
        # record the activation of this method
        self._thread_local.changed_activations.append(self)
        # propagate change to our container-parents
        for container_parent in self._container_parents:
            container_parent.changed()
        # allow change to propagate to any direct (orm) parents
        r = super(DMMutableContainer, self).changed()
        # remove record of our own activation
        self._thread_local.changed_activations.pop()
        return r


class DMMutableDict(DMMutableContainer, MutableDict):
    def _common_init_update_inner(self, *args, **kwargs):
        # arg handling of `__init__` and `update` on a dict turn out to be very similar - this is the common core:
        # do a slightly intricate little dance here to make sure we intercept and coerce any newly assigned json-like
        # values
        if args:
            if hasattr(args[0], "items") and callable(args[0].items):
                new_arg_0 = {k: self.coerce_contained(v) for k, v in iteritems(args[0])}
            else:
                new_arg_0 = tuple((k, self.coerce_contained(v)) for k, v in args[0])
            args = (new_arg_0,) + args[1:]
        kwargs = {k: self.coerce_contained(v) for k, v in iteritems(kwargs)}
        return args, kwargs

    #
    # catch all mutating methods of dict which accept new members and ensure they are appripriately coerced
    #

    def __init__(self, *args, **kwargs):
        args, kwargs = self._common_init_update_inner(*args, **kwargs)
        super(DMMutableDict, self).__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        # intercept and coerce any newly assigned json-like values
        r = super(DMMutableDict, self).__setitem__(key, self.coerce_contained(value))
        self.changed()
        return r

    def setdefault(self, *args, **kwargs):
        # intercept and coerce any newly assigned json-like values
        if len(args) > 1:
            args[1] = self.coerce_contained(args[1])
        r = super(DMMutableDict, self).setdefault(*args, **kwargs)
        self.changed()
        return r

    def update(self, *args, **kwargs):
        args, kwargs = self._common_init_update_inner(*args, **kwargs)
        r = super(DMMutableDict, self).update(*args, **kwargs)
        self.changed()
        return r


class DMMutableList(DMMutableContainer, list):
    #
    # catch all mutating methods of list and make sure they advertize the change
    #

    def __delitem__(self, *args, **kwargs):
        r = super(DMMutableList, self).__delitem__(*args, **kwargs)
        self.changed()
        return r

    def __delslice__(self, *args, **kwargs):
        r = super(DMMutableList, self).__delslice__(*args, **kwargs)
        self.changed()
        return r

    def __imul__(self, *args, **kwargs):
        r = super(DMMutableList, self).__imul__(*args, **kwargs)
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

    #
    # additionally ensure methods which accept new members appropriately coerce them
    #

    def __setitem__(self, key, value):
        # intercept and coerce any newly assigned json-like values
        if isinstance(key, slice):
            value = tuple(self.coerce_contained(v) for v in value)
        else:
            value = self.coerce_contained(value)
        r = super(DMMutableList, self).__setitem__(key, value)
        self.changed()
        return r

    def __setslice__(self, i, j, seq):
        # apparently though this method is deprecated since python 2.0 we still have to implement it as the cpython
        # builtin types still implement it.
        # intercept and coerce any newly assigned json-like values
        seq = tuple(self.coerce_contained(v) for v in seq)
        r = super(DMMutableList, self).__setslice__(i, j, seq)
        self.changed()
        return r

    def __iadd__(self, seq):
        # intercept and coerce any newly assigned json-like values
        seq = tuple(self.coerce_contained(v) for v in seq)
        r = super(DMMutableList, self).__iadd__(seq)
        self.changed()
        return r

    def append(self, value):
        r = super(DMMutableList, self).append(self.coerce_contained(value))
        self.changed()
        return r

    def extend(self, seq):
        seq = tuple(self.coerce_contained(v) for v in seq)
        r = super(DMMutableList, self).extend(seq)
        self.changed()
        return r

    def insert(self, i, value):
        r = super(DMMutableList, self).insert(i, self.coerce_contained(value))
        self.changed()
        return r
