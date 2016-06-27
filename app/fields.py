from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.types import TypeDecorator

from .utils import strip_whitespace_from_data, purge_nulls_from_data


class SanitizedJSON(TypeDecorator):
    impl = JSON

    def process_bind_param(self, value, dialect):
        if value is None:
            # it's not our job to prevent nulls (not here, anyway)
            return value

        value = strip_whitespace_from_data(value)
        value = purge_nulls_from_data(value)

        return value

    def coerce_compared_value(self, op, value):
        # required to prevent `process_bind_param` from being used to transform comparison values (which for JSON
        # includes key-lookup strings destined for the sql)
        return self.impl.coerce_compared_value(op, value)
