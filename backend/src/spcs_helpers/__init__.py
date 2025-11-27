def get_secret(secret_name: str, key: str = "secret_string") -> str | None:
    """
    Read a secret from the Snowflake SPCS secrets directory.

    When using objectReference in SPCS, secrets are mounted as files at:
    /secrets/<secret_name>/<key>

    Args:
        secret_name: The name of the secret reference (e.g., 'serper')
        key: The key within the secret (default: 'secret_string')

    Returns:
        The secret value as a string, or None if not found
    """
    import os

    secret_path = f"/secrets/{secret_name}/{key}"

    if os.path.exists(secret_path):
        with open(secret_path, 'r') as f:
            return f.read().strip()

    return None


def get_serper_api_key() -> str | None:
    """
    Get the Serper API key from SPCS secrets or environment variable.

    Tries in order:
    1. SPCS secret file at /secrets/serper/secret_string
    2. Environment variable SERPER_API_KEY (for local development)

    Returns:
        The API key or None if not found
    """
    import os

    # First try SPCS secret file
    api_key = get_secret("serper", "secret_string")
    if api_key:
        return api_key

    # Fallback to environment variable (for local dev)
    return os.getenv('SERPER_API_KEY')
