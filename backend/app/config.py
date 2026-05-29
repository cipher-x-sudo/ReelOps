from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://reelops:reelops@postgres:5432/reelops"
    secret_key: str = Field("dev-secret-change-me", alias="REELOPS_SECRET_KEY")
    access_token_minutes: int = 60 * 12

    admin_user: str = Field("owner@reelops.app", alias="REELOPS_ADMIN_USER")
    admin_password: str = Field("change-me-now", alias="REELOPS_ADMIN_PASSWORD")

    artifacts_dir: Path = Field(Path("artifacts"), alias="ARTIFACTS_DIR")
    niches_dir: Path = Field(Path("niches"), alias="NICHES_DIR")
    niche_configs_dir: Path = Field(Path("configs/niches"), alias="NICHE_CONFIGS_DIR")

    flow2api_base_url: str = Field("http://localhost:8000", alias="FLOW2API_BASE_URL")
    flow2api_api_key: str = Field("", alias="FLOW2API_API_KEY")

    llm_provider: str = Field("openrouter", alias="LLM_PROVIDER")
    llm_model: str = Field("openai/gpt-4.1-mini", alias="LLM_MODEL")
    openrouter_api_key: str = Field("", alias="OPENROUTER_API_KEY")
    local_llm_base_url: str = Field("", alias="LOCAL_LLM_BASE_URL")
    local_llm_api_key: str = Field("", alias="LOCAL_LLM_API_KEY")

    tts_provider: str = Field("disabled", alias="TTS_PROVIDER")
    tts_api_key: str = Field("", alias="TTS_API_KEY")
    tts_voice: str = Field("", alias="TTS_VOICE")

    render_mode: Literal["remotion", "manifest_only"] = Field("remotion", alias="REELOPS_RENDER_MODE")

    @property
    def normalized_database_url(self) -> str:
        if self.database_url.startswith("postgres://"):
            return "postgresql+psycopg://" + self.database_url[len("postgres://") :]
        if self.database_url.startswith("postgresql://"):
            return "postgresql+psycopg://" + self.database_url[len("postgresql://") :]
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
