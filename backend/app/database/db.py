"""
Database connection and engine management for BlendX Core.

Provides a SQLAlchemy engine for Snowflake, supporting both OAuth and username/password authentication based on environment and settings.
Uses dependency injection pattern for database connections to avoid session deprecation issues.
"""

import logging
import os
from typing import Generator

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from snowflake.sqlalchemy import URL
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config.settings import get_settings
from app.utils.spcs_helper import get_effective_warehouse

logger = logging.getLogger(__name__)
settings = get_settings()


def _read_fresh_oauth_token():
    """
    Read a fresh OAuth token from the mounted file.

    Returns:
        str: The OAuth token read from the file

    Raises:
        FileNotFoundError: If the token file is not found at the expected path
    """
    try:
        with open("/snowflake/session/token", "r") as token_file:
            token = token_file.read().strip()
            logger.debug("Fresh OAuth token read from file")
            return token
    except FileNotFoundError as exc:
        logger.error("OAuth token not found at '/snowflake/session/token'.")
        raise exc


def create_snowflake_engine_with_private_key():
    """Create SQLAlchemy engine for Snowflake using private key authentication."""
    logger.info("Creating Snowflake engine with private key authentication")
    # Treat empty passphrase as None for unencrypted keys
    passphrase = settings.snowflake_privatekey_password
    password_bytes = passphrase.encode() if passphrase else None

    private_key_raw = settings.snowflake_private_key_raw
    private_key_path = settings.snowflake_private_key_path

    if private_key_raw:
        # GitHub Actions case - key is provided as content
        # Check if it looks like a file path (doesn't start with -----BEGIN)
        if not private_key_raw.startswith("-----BEGIN"):
            # It might be a file path, try to read it
            if os.path.exists(private_key_raw):
                with open(private_key_raw, "rb") as key:
                    key_data = key.read()
            else:
                # Treat as raw key content
                key_data = private_key_raw.encode()
        else:
            # It's the actual PEM key content
            key_data = private_key_raw.encode()
    elif private_key_path and os.path.exists(private_key_path):
        # Local case - read from file path
        with open(private_key_path, "rb") as key:
            key_data = key.read()
    else:
        raise ValueError(
            "No valid private key found. Set either SNOWFLAKE_PRIVATE_KEY_RAW "
            "with key content or SNOWFLAKE_PRIVATE_KEY_PATH with path to key file."
        )

    p_key = serialization.load_pem_private_key(
        key_data,
        password=password_bytes,
        backend=default_backend(),
    )

    pkb = p_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    # Get effective warehouse (base name + env prefix from database if present)
    effective_warehouse = get_effective_warehouse() or settings.snowflake_warehouse

    logger.info(f"Using warehouse: {effective_warehouse}")

    return create_engine(
        URL(
            account=settings.snowflake_account,
            host=settings.snowflake_host,
            port=443,
            warehouse=effective_warehouse,
            database=settings.snowflake_database,
            schema=settings.snowflake_schema,
            role=settings.snowflake_role,
            user=settings.snowflake_user,
            authenticator="snowflake",
        ),
        echo=False,
        connect_args={
            "private_key": pkb,
        },
    )


def create_snowflake_engine():
    """
    Create and return a new SQLAlchemy engine configured for Snowflake.

    This function creates a new engine for each call, configured based on application settings.
    When OAuth authentication is enabled, it always reads a fresh token from the mounted file.
    For non-OAuth environments, it uses username/password authentication.

    Returns:
        Engine: A configured SQLAlchemy engine for Snowflake

    Raises:
        FileNotFoundError: If OAuth is enabled but the token file is not found
    """

    auth_method = (settings.snowflake_authmethod or "").lower()
    env = settings.environment.upper()
    allowed_envs = {"DEVELOPMENT", "SHARED", "STAGING", "PRODUCTION", "UAT"}
    token_file_exists = os.path.exists("/snowflake/session/token")
    # Only use OAuth if auth method is oauth, environment allows it, AND token file exists
    # This allows local development without the token file, falling back to private key auth
    use_oauth = auth_method == "oauth" and env in allowed_envs and token_file_exists

    if auth_method == "oauth" and env in allowed_envs and not token_file_exists:
        logger.info("OAuth requested but token file not found, falling back to private key authentication")

    logger.info(f"Using oauth value: {use_oauth}")

    if use_oauth:
        logger.info("Creating Snowflake engine with fresh OAuth token")

        # ALWAYS read fresh token from file
        oauth_token = _read_fresh_oauth_token()

        # In SPCS with OAuth, we only need database, schema, warehouse
        # The token contains account and host information
        # Only pass account/host if they're explicitly set (for local testing)
        url_params = {
            "database": settings.snowflake_database,
            "schema": settings.snowflake_schema,
            "authenticator": "oauth",
            "token": oauth_token,
        }

        # Get effective warehouse (base name + env prefix from database if present)
        effective_warehouse = get_effective_warehouse()
        if effective_warehouse:
            url_params["warehouse"] = effective_warehouse
        else:
            logger.warning("Could not determine warehouse name")

        # Only include account/host if they're non-empty (for local OAuth testing)
        # Empty strings should not be passed to avoid DNS resolution errors
        if settings.snowflake_account and settings.snowflake_account.strip():
            url_params["account"] = settings.snowflake_account
        if settings.snowflake_host and settings.snowflake_host.strip():
            url_params["host"] = settings.snowflake_host

        logger.info(f"Creating OAuth connection with params: {list(url_params.keys())}")
        logger.info(f"Database: {url_params.get('database')}, Schema: {url_params.get('schema')}, Warehouse: {url_params.get('warehouse', 'not set')}")

        engine = create_engine(
            URL(**url_params),
            poolclass=None,
            echo=False,
        )

        return engine

    else:
        return create_snowflake_engine_with_private_key()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions that ensures proper connection lifecycle management.

    This function implements the dependency injection pattern for database sessions.
    It creates a new engine and session for each request and properly closes both when done,
    ensuring that database connections are not leaked. This function should be used with
    FastAPI's Depends() to inject a session into route handlers.

    Example:
        @app.get("/items/")
        def read_items(db: Session = Depends(get_db)):
            # Use db session for database operations
            return db.query(Item).all()

    Yields:
        Session: SQLAlchemy session for database operations

    Notes:
        The session is automatically closed in the finally block, ensuring proper
        resource cleanup even if exceptions occur during request processing.
    """

    engine = create_snowflake_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


def get_new_db_session():
    """
    Create and return a new SQLAlchemy session for background tasks or event listeners.

    This function should be used for non-request-scoped operations (e.g., in background tasks,
    event listeners, or startup/shutdown events) to avoid transaction state issues that can occur
    when reusing request-scoped sessions. Each call creates a new engine and session.

    Returns:
        Session: A new SQLAlchemy session instance for database operations.
    """
    engine = create_snowflake_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()