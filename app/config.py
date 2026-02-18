# import os
# from functools import lru_cache
# from pydantic import BaseModel


# class Settings(BaseModel):
#     app_name: str = "Transaction Webhook Service"
#     environment: str = os.getenv("ENVIRONMENT", "local")
#     database_url: str = os.getenv(
#         "DATABASE_URL",
#         "sqlite:///./transactions.db",
#     )
#     redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
#     api_prefix: str = "/v1"


# @lru_cache
# def get_settings() -> Settings:
#     return Settings()

import os
from functools import lru_cache
from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "Transaction Webhook Service"
    environment: str = os.getenv("ENVIRONMENT", "local")
    database_url: str = (
        os.getenv("DATABASE_URL", "sqlite:///./transactions.db")
        .replace("postgres://", "postgresql://", 1)
    )
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    api_prefix: str = "/v1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
