"""Application settings loaded from environment variables (.env)."""
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- General ---
    app_name: str = "RecruitFlow"
    environment: Literal["dev", "test", "prod"] = "dev"
    debug: bool = False
    # Demo data (admin/recruiter + sample records). Seed refuses to run in prod
    # unless this flag is explicitly enabled (used by the public demo deployment).
    allow_seed: bool = False

    # --- Database ---
    postgres_user: str = "recruitflow"
    postgres_password: str = "recruitflow_dev_password"
    postgres_db: str = "recruitflow"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # --- JWT / Auth ---
    secret_key: str = "change-me-in-production-please-use-openssl-rand-hex-32"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 12  # 12 hours
    login_rate_limit_attempts: int = 5
    login_rate_limit_seconds: int = 300  # 5 minutes

    # --- CORS ---
    # Comma-separated list of origins, e.g. "http://localhost:5173,https://example.com"
    cors_origins: str = "http://localhost:5173,http://localhost:8080"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # --- File storage (resumes) ---
    # Pluggable: "local" (Docker volume) or "s3" (S3-compatible, future).
    storage_backend: Literal["local", "s3"] = "local"
    storage_local_path: str = "/data/uploads"
    max_upload_size_mb: int = 10

    # --- GDPR ---
    candidate_retention_days: int = 0  # 0 = disabled; else auto-anonymize after N days


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
