from app.api.helpers import Service
from app.models import ApiKey, db
from app.api.helpers import generate_random_token
from datetime import datetime


class ApiKeyService(Service):
    __model__ = ApiKey

    def __init__(self, *args, **kwargs):
        super(ApiKeyService, self).__init__(*args, **kwargs)

    def get_key(self, key):
        query = (
            db
            .session
            .query(ApiKey)
            .filter(
                ApiKey.key == key,
                ApiKey.revoked_at.is_(None)
            )
            .order_by(ApiKey.created_at.desc())
        )
        return query.first()

    def generate(self, user_id, length=32):
        api_key = ApiKey(user_id=user_id, key=generate_random_token(length=length))
        self.save(api_key)
        return api_key.key

    def revoke(self, key):
        keys = (
            db
            .session
            .query(ApiKey)
            .filter(
                ApiKey.key == key,
                ApiKey.revoked_at.is_(None)
            )
            .all()
        )
        for key in keys:
            key.revoke()
            self.save(key)
        return True
