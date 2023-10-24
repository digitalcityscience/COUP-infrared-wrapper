import json

from fastapi.encoders import jsonable_encoder

import redis
from infrared_wrapper_api.config import RedisConnectionConfig


class Cache:
    def __init__(
        self, connection_config: RedisConnectionConfig, key_prefix: str, ttl_days: int
    ):
        self._redis = redis.Redis(
            host=connection_config.host,
            port=connection_config.port,
            db=connection_config.db,
            username=connection_config.username,
            password=connection_config.password,
            ssl=connection_config.ssl,
            decode_responses=True,
        )
        self._key_prefix = key_prefix
        self._ttl_days = ttl_days

    def get(self, *, key: str) -> dict:
        key = self._make_key(key)
        serialized_value = self._redis.get(key)
        return None if serialized_value is None else json.loads(serialized_value)

    def put(self, *, key: str, value: dict) -> None:
        key = self._make_key(key)
        jsonable_value = jsonable_encoder(value)
        serialized_value = json.dumps(jsonable_value)
        ttl = self._ttl_days * 86400
        self._redis.setex(key, ttl, serialized_value)

    def delete(self, *, key: str) -> None:
        key = self._make_key(key)
        self._redis.delete(key)

    def _make_key(self, key: str) -> str:
        return f"{self._key_prefix}:{key}"
