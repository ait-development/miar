"""Configuration helpers shared between services."""

from __future__ import annotations

from functools import lru_cache

from pydantic import AnyUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from . import constants


class Settings(BaseSettings):
    """Base environmental configuration for a microservice."""

    service_name: str = Field(default="service")
    service_role: str = Field(default="service")
    service_port: int = Field(default=8000)
    rabbitmq_url: AnyUrl = Field(alias="RABBITMQ_URL")
    log_level: str = Field(default="INFO")
    sleep_symbol: str | None = Field(default=None)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",
    )

    @property
    def symbol_route(self):
        if self.sleep_symbol is None:
            return None
        return constants.SYMBOL_ROUTES.get(self.sleep_symbol)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]

