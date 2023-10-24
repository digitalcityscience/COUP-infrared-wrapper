from typing import Literal, Optional

from pydantic import BaseSettings, Field


class RedisConnectionConfig(BaseSettings):
    host: str = Field(..., env="REDIS_HOST")
    port: int = Field(..., env="REDIS_PORT")
    db: int = Field(..., env="REDIS_DB")
    username: str = Field(..., env="REDIS_USERNAME")
    password: str = Field(..., env="REDIS_PASSWORD")
    ssl: bool = Field(..., env="REDIS_SSL")


class CacheRedis(BaseSettings):
    connection: RedisConnectionConfig = Field(default_factory=RedisConnectionConfig)
    key_prefix: str = "infrared_simulations"
    ttl_days: int = Field(30, env="REDIS_CACHE_TTL_DAYS")

    @property
    def redis_url(self) -> str:
        return f"redis://:{self.connection.password}@{self.connection.host}:{self.connection.port}"

    @property
    def broker_url(self) -> str:
        return f"{self.redis_url}/0"

    @property
    def result_backend(self) -> str:
        return f"{self.redis_url}/1"


class BrokerCelery(BaseSettings):
    worker_concurrency: int = 10
    result_expires: bool = None  # Do not delete results from cache.
    result_persistent: bool = True
    enable_utc: bool = True
    task_default_queue: str = Field(..., env="CELERY_DEFAULT_QUEUE")


class InfraredCommunication(BaseSettings):
    url: str = Field(..., env="INFRARED_URL")
    user: str = Field(..., env="INFRARED_USERNAME")
    password: str = Field(..., env="INFRARED_PASSWORD")


class InfraredCalculation(BaseSettings):
    max_bbox_size: int = Field(default=500)  # bbox size in meters
    bbox_buffer: int = Field(default=100)  # buffer will be trimmed from result as results at bbox edges are faulty
    analysis_resolution: int = Field(default=10)  # resolution of analysis in meters


class Settings(BaseSettings):
    title: str = Field(..., env="APP_TITLE")
    description: str = Field(..., env="APP_DESCRIPTION")
    version: str = Field(..., env="APP_VERSION")
    debug: bool = Field(..., env="DEBUG")
    environment: Optional[Literal["LOCALDEV", "PROD"]] = Field(..., env="ENVIRONMENT")
    cache: CacheRedis = Field(default_factory=CacheRedis)
    broker: BrokerCelery = Field(default_factory=BrokerCelery)
    infrared_communication: InfraredCommunication = Field(default_factory=InfraredCommunication)
    infrared_calculation: InfraredCalculation = Field(default_factory=InfraredCalculation)

settings = Settings()
