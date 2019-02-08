import pendulum
from app.api.helpers import Service
from app import db
from app.models import KeyValue


class KeyValueService(Service):
    __model__ = KeyValue

    def __init__(self, *args, **kwargs):
        super(KeyValueService, self).__init__(*args, **kwargs)

    def upsert(self, key, data):
        existing = self.find(key=key).one_or_none()
        if existing:
            saved = self.update(existing, data=data)
        else:
            saved = self.create(key=key, data=data)

        return {
            "key": saved.key,
            "data": saved.data,
            "updated_at": saved.updated_at
        } if saved else None

    def get_by_key(self, key):
        key_value = (
            db
            .session
            .query(
                KeyValue.key,
                KeyValue.data,
                KeyValue.updated_at
            )
            .filter(KeyValue.key == key)
            .one_or_none()
        )

        return key_value._asdict() if key_value else None

    def get_by_keys(self, *keys):
        key_values = (
            db
            .session
            .query(
                KeyValue.key,
                KeyValue.data,
                KeyValue.updated_at
            )
            .filter(KeyValue.key.in_(keys))
            .all()
        )

        return [kv._asdict() for kv in key_values]

    def convert_to_object(self, key_values):
        result = {}
        for kv in key_values:
            result[kv['key']] = kv['data']

        return result
