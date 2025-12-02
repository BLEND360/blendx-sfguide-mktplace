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
# In container: /app/config/settings.py -> parent.parent = /app
# Local dev: backend/app/config/settings.py -> parent.parent = backend/app, parent.parent.parent = backend
_CONFIG_DIR = Path(__file__).resolve().parent
_APP_DIR = _CONFIG_DIR.parent  # backend/app or /app in container

# Check for .env in multiple locations (for local dev vs container)
# 1. backend/.env (local development)
# 2. backend/app/.env (container or alternative local setup)
_BACKEND_DIR = _APP_DIR.parent
if (_BACKEND_DIR / ".env").exists():
    ENV_FILE = _BACKEND_DIR / ".env"
else:
    ENV_FILE = _APP_DIR / ".env"


class PersistenceGranularity(str, Enum):
    """Supported persistence granularity levels"""

    EXECUTION_GROUPS = "execution_groups"  # Only execution groups
    CREW = "crew"  # Crew + execution groups
    AGENTS = "agents"  # Agents + crews + execution groups
    TASKS = "tasks"  # Tasks + agents + crews + execution groups
    TOOLS = "tools"  # Tools + tasks + agents + crews + execution groups
    ALL = "all"


class FlowGranularity(str, Enum):
    """Supported flow granularity levels"""

    FLOWS = "flows"  # Only flows
    METHODS = "methods"  # Methods + flows
    ALL = "all"  # All


class LLMProvider(str, Enum):
    """Supported LLM providers"""

    SNOWFLAKE = "snowflake"
    OPENAI = "openai"


class EmbeddingProvider(str, Enum):
    """Supported embedding providers"""

    SNOWFLAKE = "snowflake"
    OPENAI = "openai"


class Settings(BaseSettings):
    """Application settings"""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_prefix="",
        env_map={
            "persistence_granularity": "PERSISTENCE_GRANULARITY",
            "log_level": "LOG_LEVEL",
            "flow_granularity": "FLOW_GRANULARITY",
            "environment": "ENVIRONMENT",
            "snowflake_account": "SNOWFLAKE_ACCOUNT",
            "snowflake_user": "SNOWFLAKE_USER",
            "snowflake_warehouse": "SNOWFLAKE_WAREHOUSE",
            "snowflake_database": "SNOWFLAKE_DATABASE",
            "snowflake_schema": "SNOWFLAKE_SCHEMA",
            "snowflake_role": "SNOWFLAKE_ROLE",
            "snowflake_host": "SNOWFLAKE_HOST",
            "snowflake_url": "SNOWFLAKE_URL",
            "snowflake_authmethod": "SNOWFLAKE_AUTHMETHOD",
            "snowflake_service_user": "SNOWFLAKE_SERVICE_USER",
            "snowflake_private_key_path": "SNOWFLAKE_PRIVATE_KEY_PATH",
            "snowflake_privatekey_password": "SNOWFLAKE_PRIVATEKEY_PASSWORD",
            "snowflake_private_key_raw": "SNOWFLAKE_PRIVATE_KEY_RAW",
            "snowflake_stage_semantic_model": "SNOWFLAKE_STAGE_SEMANTIC_MODEL",
            "snowflake_semantic_model_filename": "SNOWFLAKE_SEMANTIC_MODEL_FILENAME",
            "snowflake_search_service_name": "SNOWFLAKE_SEARCH_SERVICE_NAME",
            "llm_provider": "LLM_PROVIDER",
            "llm_model_name": "LLM_MODEL_NAME",
            "embedding_provider": "EMBEDDING_PROVIDER",
            "embedding_model_name": "EMBEDDING_MODEL_NAME",
            "event_logging_enabled": "EVENT_LOGGING_ENABLED",
            "database_logging_enabled": "DATABASE_LOGGING_ENABLED",
            "opik": "OPIK",
            "blendx_hub_url": "BLENDX_HUB_URL",
            "blendx_hub_database": "BLENDX_HUB_DATABASE",
            "blendx_hub_schema": "BLENDX_HUB_SCHEMA",
            "blendx_hub_warehouse": "BLENDX_HUB_WAREHOUSE",
            "nl_generator_default_model": "NL_GENERATOR_DEFAULT_MODEL",
            "crew_execution_database": "CREW_EXECUTION_DATABASE",
            "crew_execution_schema": "CREW_EXECUTION_SCHEMA",
            "crew_execution_table": "CREW_EXECUTION_TABLE",
            "workflows_database": "WORKFLOWS_DATABASE",
            "workflows_schema": "WORKFLOWS_SCHEMA",
            "workflows_table": "WORKFLOWS_TABLE",
        },
    )

    # Log level setting
    log_level: str = Field("INFO")

    # Persistence granularity setting
    persistence_granularity: PersistenceGranularity = Field(PersistenceGranularity.ALL)

    # Flow granularity setting
    flow_granularity: FlowGranularity = Field(FlowGranularity.ALL)

    # Environment setting
    environment: str = Field("SHARED")

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

    # Snowflake Tools settings
    snowflake_stage_semantic_model: Optional[str] = Field(None)
    snowflake_semantic_model_filename: Optional[str] = Field(None)
    snowflake_search_service_name: str = Field("SNOWFLAKE_SEARCH_SERVICE_NAME")

    # LLM settings
    llm_provider: LLMProvider = Field(LLMProvider.SNOWFLAKE)
    llm_model_name: str = Field("claude-3-5-sonnet")

    # Embedding settings (independent from LLM)
    embedding_provider: EmbeddingProvider = Field(EmbeddingProvider.SNOWFLAKE)
    embedding_model_name: str = Field("snowflake-arctic-embed-m")

    # OpenAI settings (when using OpenAI provider)
    openai_api_key: Optional[str] = Field(None)

    # Event logging setting
    event_logging_enabled: bool = Field(False)

    # Database logging setting
    database_logging_enabled: bool = Field(False)

    # OpiK settings
    opik: bool = Field(False)

    # BlendX Hub settings
    blendx_hub_url: Optional[str] = Field(None, description="BlendX Hub API URL")
    blendx_hub_database: Optional[str] = Field(
        None, description="BlendX Hub database name"
    )
    blendx_hub_schema: Optional[str] = Field(None, description="BlendX Hub schema name")
    blendx_hub_warehouse: Optional[str] = Field(
        None, description="BlendX Hub warehouse name"
    )

    # NL Generator default model (optional override)
    nl_generator_default_model: Optional[str] = Field(
        None, description="Default NL generator model for Snowflake"
    )

    # Crew execution table configuration
    crew_execution_database: Optional[str] = Field(
        None, description="Database for crew execution results table (defaults to snowflake_database if not set)"
    )
    crew_execution_schema: Optional[str] = Field(
        None, description="Schema for crew execution results table (defaults to snowflake_schema if not set)"
    )
    crew_execution_table: str = Field(
        "crew_execution_results", description="Table name for crew execution results"
    )

    # Workflows table configuration
    workflows_database: Optional[str] = Field(
        None, description="Database for workflows table (defaults to snowflake_database if not set)"
    )
    workflows_schema: Optional[str] = Field(
        None, description="Schema for workflows table (defaults to snowflake_schema if not set)"
    )
    workflows_table: str = Field(
        "workflows", description="Table name for workflows"
    )

    @property
    def private_key(self) -> str:
        """Read and cache the private key from the configured path"""
        try:
            with open(self.snowflake_private_key_path, "r") as key_file:
                return key_file.read().strip()
        except Exception as e:
            raise ValueError(
                f"Failed to read private key from {self.snowflake_private_key_path}: {str(e)}"
            )

    @property
    def crew_execution_full_table_name(self) -> str:
        """Get the fully qualified table name for crew execution results.

        If database is not set, returns schema.table (relies on session context).
        If database is set, returns database.schema.table.
        """
        schema = self.crew_execution_schema or self.snowflake_schema
        return f"{schema}.{self.crew_execution_table}"

    @property
    def workflows_full_table_name(self) -> str:
        """Get the fully qualified table name for workflows.

        If database is not set, returns schema.table (relies on session context).
        If database is set, returns database.schema.table.
        """
        database = self.workflows_database or self.snowflake_database
        schema = self.workflows_schema or self.snowflake_schema
        if database:
            return f"{database}.{schema}.{self.workflows_table}"
        return f"{schema}.{self.workflows_table}"

    def get_nl_generator_default_model(self, fallback_model: Optional[str] = None) -> Optional[str]:
        """Get the default NL generator model for Snowflake.

        Returns the configured model or the fallback if not set.
        """
        return self.nl_generator_default_model or fallback_model


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
