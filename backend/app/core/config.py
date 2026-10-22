"""应用配置。

优先级：环境变量 > .env 文件 > 代码默认值。

用 AliasChoices 是为了让同一份配置适配两种运行环境：
- 容器内：compose 注入 DB_HOST=db / DB_PASSWORD=... （用服务名寻址）
- 本机：直接读 .env 里的 POSTGRES_*，host 回落到 127.0.0.1（端口已发布到本机）
"""

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py → parents[2] 是：
#   本机  = D:\personal-agent\backend
#   容器  = /app
_BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Knowledge Agent API"
    app_version: str = "0.1.0"
    # 上传文件落盘目录；容器里由 compose 注入 DATA_DIR=/app/data
    data_dir: Path = _BACKEND_DIR / "data"
    # 单文件大小上限，默认 5 MB
    max_upload_bytes: int = 5 * 1024 * 1024

    db_host: str = "127.0.0.1"
    db_port: int = 5432
    db_name: str = Field(
        default="knowledge",
        validation_alias=AliasChoices("DB_NAME", "POSTGRES_DB"),
    )
    db_user: str = Field(
        default="knowledge",
        validation_alias=AliasChoices("DB_USER", "POSTGRES_USER"),
    )
    db_password: str = Field(
        default="",
        validation_alias=AliasChoices("DB_PASSWORD", "POSTGRES_PASSWORD"),
    )

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def safe_database_url(self) -> str:
        """密码打码版，用于日志和排查。"""
        return (
            f"postgresql+asyncpg://{self.db_user}:***"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
