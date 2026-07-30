from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = (
        "postgresql+asyncpg://teacher_assistant:teacher_assistant_dev@database:5432/"
        "teacher_assistant"
    )
    testing: bool = False
    log_level: str = "info"
    openai_api_key: SecretStr | None = None
    codex_auth_home: Path = Path("/var/lib/teacher-assistant/codex")
    codex_model: str = "gpt-5.6-sol"
    ai_allowed_models: str = "gpt-5.6-sol,gpt-5.6-terra,gpt-5.6-luna"
    codex_timeout_seconds: int = Field(default=90, ge=10, le=600)
    codex_max_context_events: int = Field(default=1000, ge=1, le=5000)
    assistant_proposal_ttl_minutes: int = Field(default=30, ge=5, le=1440)
    course_storage_root: Path = Path("/data/course_content")
    course_max_upload_mb: int = Field(default=25, ge=1, le=500)

    @property
    def course_max_upload_bytes(self) -> int:
        return self.course_max_upload_mb * 1024 * 1024

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
