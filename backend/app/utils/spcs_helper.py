"""
SPCS Helpers.

Utilities for reading secrets from Snowflake SPCS (Snowpark Container Services)
or from local development environment.
"""

import os
from pathlib import Path

# Get the backend directory for local secrets
_CURRENT_DIR = Path(__file__).resolve().parent
_APP_DIR = _CURRENT_DIR.parent  # backend/app
_BACKEND_DIR = _APP_DIR.parent  # backend
_LOCAL_SECRETS_DIR = _BACKEND_DIR / "secrets"


def get_secret(secret_name: str, key: str = "secret_string") -> str | None:
    """
    Read a secret from SPCS secrets directory or local secrets directory.

    Tries in order:
    1. SPCS secret file at /secrets/<secret_name>/<key> (production)
    2. Local flat file at backend/secrets/<SECRET_NAME> (simple local development)
    3. Local nested file at backend/secrets/<secret_name>/<key> (SPCS-compatible local)

    When using objectReference in SPCS, secrets are mounted as files at:
    /secrets/<secret_name>/<key>

    For local development, you can use either:
    - Simple: backend/secrets/SERPER_API_KEY (flat file with the value)
    - SPCS-compatible: backend/secrets/serper/secret_string

    Args:
        secret_name: The name of the secret reference (e.g., 'serper')
        key: The key within the secret (default: 'secret_string')

    Returns:
        The secret value as a string, or None if not found
    """
    # Try SPCS path first (production)
    spcs_secret_path = f"/secrets/{secret_name}/{key}"
    if os.path.exists(spcs_secret_path):
        with open(spcs_secret_path, "r") as f:
            return f.read().strip()

    # Try local flat file (simple development) - e.g., secrets/SERPER_API_KEY
    local_flat_path = _LOCAL_SECRETS_DIR / f"{secret_name.upper()}_API_KEY"
    if local_flat_path.exists() and local_flat_path.is_file():
        return local_flat_path.read_text().strip()

    # Try local nested directory (SPCS-compatible) - e.g., secrets/serper/secret_string
    local_nested_path = _LOCAL_SECRETS_DIR / secret_name / key
    if local_nested_path.exists():
        return local_nested_path.read_text().strip()

    return None


def get_effective_warehouse() -> str | None:
    """
    Get the effective warehouse name for this SPCS service.

    Takes SNOWFLAKE_WAREHOUSE env var (e.g., BLENDX_APP_WH) and prefixes it
    with the environment suffix from SNOWFLAKE_DATABASE if present.

    Examples:
    - SNOWFLAKE_DATABASE=BLENDX_APP_INSTANCE, SNOWFLAKE_WAREHOUSE=BLENDX_APP_WH -> BLENDX_APP_WH
    - SNOWFLAKE_DATABASE=BLENDX_APP_INSTANCE_QA, SNOWFLAKE_WAREHOUSE=BLENDX_APP_WH -> QA_BLENDX_APP_WH
    - SNOWFLAKE_DATABASE=BLENDX_APP_INSTANCE_STABLE, SNOWFLAKE_WAREHOUSE=BLENDX_APP_WH -> STABLE_BLENDX_APP_WH

    Returns:
        The effective warehouse name or None if SNOWFLAKE_WAREHOUSE not set
    """
    base_warehouse = os.getenv("SNOWFLAKE_WAREHOUSE", "").strip()
    if not base_warehouse:
        return None

    database = os.getenv("SNOWFLAKE_DATABASE", "").strip()
    if not database:
        return base_warehouse

    # Expected prefix for the database name
    base_prefix = "BLENDX_APP_INSTANCE"

    if database == base_prefix:
        # No environment suffix
        return base_warehouse
    elif database.startswith(base_prefix + "_"):
        # Has environment suffix (e.g., _QA, _STABLE)
        env_suffix = database[len(base_prefix) + 1:]  # Extract QA, STABLE, etc.
        return f"{env_suffix}_{base_warehouse}"

    # Database doesn't match expected pattern, return base warehouse
    return base_warehouse


def get_serper_api_key() -> str | None:
    """
    Get the Serper API key from SPCS secrets, local secrets, or environment variable.

    Tries in order:
    1. SPCS secret file at /secrets/serper/secret_string (production)
    2. Local secret file at backend/secrets/serper/secret_string (local development)
    3. Environment variable SERPER_API_KEY (fallback)

    Returns:
        The API key or None if not found
    """
    # First try SPCS/local secret file
    api_key = get_secret("serper", "secret_string")
    if api_key:
        return api_key

    # Fallback to environment variable
    return os.getenv("SERPER_API_KEY")
