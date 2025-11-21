"""
Application configuration and environment settings for BlendX Core.

Defines enums and a Pydantic-based Settings class for all environment variables and configuration options, including Snowflake, LLM, embedding, and logging settings. Provides a cached settings accessor for use throughout the application.
"""

import os
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Get the directory where this settings.py file is located
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    """Application settings"""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Environment setting
    environment: str = Field("PRODUCTION")

    # Snowflake connection settings
    snowflake_account: str = Field(
        "", description="Snowflake default account identifier"
    )
    snowflake_user: str = Field("", description="Snowflake default user name")
    snowflake_warehouse: str = Field("", description="Snowflake default warehouse name")
    snowflake_database: str = Field("", description="Snowflake default database name")
    snowflake_schema: str = Field("", description="Snowflake default database name")
    snowflake_role: str = Field("", description="Snowflake default role name")
    snowflake_host: str = Field("", description="Snowflake default host URL")

    # Snowflake LLM API settings
    snowflake_url: Optional[str] = Field(None, description="Snowflake Cortex API URL")
    snowflake_authmethod: str = Field("oauth", description="Snowflake auth method")
    snowflake_service_user: Optional[str] = Field(
        None, description="Snowflake service user"
    )

    # Private Key Authentication settings
    snowflake_private_key_path: str = Field("keys/rsa_key.p8")
    snowflake_privatekey_password: Optional[str] = Field(
        None, description="Password for encrypted private key"
    )
    snowflake_private_key_raw: Optional[str] = Field(
        None,
        description="Raw private key content (for GitHub Actions). If set, this takes precedence over the path.",
    )
    private_key: Optional[str] = Field(
        None,
        description="Private key content loaded from file or raw. Used by lite_llm_handler."
    )

    def model_post_init(self, __context) -> None:
        """Load private key after model initialization"""
        if self.snowflake_private_key_raw:
            self.private_key = self.snowflake_private_key_raw
        elif self.snowflake_private_key_path and os.path.exists(self.snowflake_private_key_path):
            try:
                with open(self.snowflake_private_key_path, 'r') as f:
                    self.private_key = f.read()
            except Exception as e:
                print(f"Warning: Could not load private key from {self.snowflake_private_key_path}: {e}")


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
