from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Authoritative baseline per TDD.md §9.1, §9.6 and ADR-002
ALGORITHM_VERSION = "roomsync-rule-v1"
WEIGHTS_VERSION = "weights-2026-01"
QUESTION_SCHEMA_VERSION = 1

CATEGORY_WEIGHTS: dict[str, int] = {
    "daily_routine": 15,
    "cleanliness": 15,
    "financial_expectations": 15,
    "privacy_and_boundaries": 15,
    "social_lifestyle": 10,
    "food_preferences": 10,
    "guest_preferences": 10,
    "work_study_environment": 10,
}


class MatchingSettings(BaseSettings):
    """Runtime settings for the private stateless matching compute service."""

    model_config = SettingsConfigDict(
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    environment: str = Field(default="local", alias="ENVIRONMENT")
    internal_service_token: str = Field(default="", alias="INTERNAL_SERVICE_TOKEN")
    service_name: str = "matching"
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @property
    def is_ready(self) -> bool:
        return bool(self.internal_service_token.strip()) and sum(CATEGORY_WEIGHTS.values()) == 100


@lru_cache(maxsize=1)
def get_settings() -> MatchingSettings:
    return MatchingSettings()

