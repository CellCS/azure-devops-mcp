# /app/config.py

from functools import lru_cache
from typing import Any, cast

from pydantic import field_validator
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


def _strip_matching_quotes(value: str) -> str:
    trimmed = value.strip()
    if len(trimmed) >= 2 and trimmed[0] == trimmed[-1] and trimmed[0] in {"'", '"'}:
        return trimmed[1:-1].strip()
    return trimmed


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

    @field_validator("azure_org", "azure_pat", "mcp_http_path", mode="before")
    @classmethod
    def normalize_string_fields(cls, value: Any) -> Any:
        if isinstance(value, str):
            return _strip_matching_quotes(value)
        return value

    @field_validator("mcp_bearer_tokens")
    @classmethod
    def validate_mcp_bearer_tokens(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("MCP_BEARER_TOKENS must be set and non-empty")

        normalized = _strip_matching_quotes(value)
        tokens = [
            _strip_matching_quotes(token)
            for token in normalized.split(",")
            if _strip_matching_quotes(token)
        ]
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
    path = _strip_matching_quotes(settings.mcp_http_path) if settings.mcp_http_path else "/mcp"
    if not path.startswith("/"):
        path = f"/{path}"
    return path
