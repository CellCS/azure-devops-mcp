# /libs/config.py

from functools import lru_cache
from typing import Any, cast

from pydantic import field_validator
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):
    azure_org: str
    azure_pat: str
    mcp_bearer_tokens: str
    mcp_http_path: str = "/devops-mcp"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("mcp_bearer_tokens")
    @classmethod
    def validate_mcp_bearer_tokens(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("MCP_BEARER_TOKENS must be set and non-empty")

        tokens = [token.strip() for token in value.split(",") if token.strip()]
        if not tokens:
            raise ValueError(
                "MCP_BEARER_TOKENS must include at least one non-empty token"
            )

        return ",".join(tokens)


@lru_cache
def get_settings() -> Settings:
    return cast(Any, Settings)()


def get_configured_mcp_tokens() -> set[str]:
    settings = get_settings()
    return {
        token.strip()
        for token in settings.mcp_bearer_tokens.split(",")
        if token.strip()
    }


def get_mcp_http_path() -> str:
    settings = get_settings()
    path = settings.mcp_http_path.strip() if settings.mcp_http_path else "/mcp"
    if not path.startswith("/"):
        path = f"/{path}"
    return path
