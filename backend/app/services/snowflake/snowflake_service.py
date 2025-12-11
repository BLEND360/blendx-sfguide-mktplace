# Libraries
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from snowflake.connector import connect
from snowflake.core import Root
from snowflake.snowpark import Session

# Local Dependencies
from app.config.settings import Settings, get_settings


class SnowflakeService:
    def __init__(self, settings: Optional[Settings] = None):
        """Initialize Snowflake service with connection details from settings"""
        self.settings = settings or get_settings()
        self._session = None
        self._root = None
        self._service_metadata = {}
        self._connection_params = None

    def _get_connection_params(
        self, override_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get connection parameters, optionally overriding with custom values.

        Args:
            override_params: Optional dictionary to override default connection parameters

        Returns:
            Dictionary containing connection parameters
        """
        base_params = {
            "account": self.settings.snowflake_account,
            "user": self.settings.snowflake_user,
            "password": self.settings.snowflake_password,
            "warehouse": self.settings.snowflake_warehouse,
            "database": self.settings.snowflake_database,
            "schema": self.settings.snowflake_schema,
            "role": self.settings.snowflake_role,
        }

        if override_params:
            base_params.update(override_params)

        # Remove None values
        return {k: v for k, v in base_params.items() if v is not None}

    def get_session(
        self, connection_params: Optional[Dict[str, Any]] = None
    ) -> Session:
        """
        Get or create Snowflake session with optional parameter overrides.

        Args:
            connection_params: Optional dictionary to override connection parameters

        Returns:
            Snowflake Session instance
        """
        # Check if we need to recreate session due to parameter changes
        current_params = self._get_connection_params(connection_params)

        if self._session is None or self._connection_params != current_params:
            self._create_session(current_params)
            self._connection_params = current_params

        return self._session

    def get_root(self, connection_params: Optional[Dict[str, Any]] = None) -> Root:
        """
        Get Root instance for accessing Snowflake objects.

        Args:
            connection_params: Optional dictionary to override connection parameters

        Returns:
            Root instance
        """
        session = self.get_session(connection_params)
        if (
            self._root is None
            or self._connection_params != self._get_connection_params(connection_params)
        ):
            self._root = Root(session)
        return self._root

    def _create_session(self, connection_params: Dict[str, Any]):
        """
        Create a new Snowflake session using appropriate authentication method.

        Args:
            connection_params: Dictionary containing connection parameters
        """
        try:
            # Close existing session if any
            if self._session:
                self.close()

            # Use the same authentication logic as the database connection
            auth_method = (self.settings.snowflake_authmethod or "").lower()
            env = self.settings.environment.upper()
            allowed_envs = {"DEVELOPMENT", "SHARED", "STAGING", "PRODUCTION", "UAT"}
            use_oauth = auth_method == "oauth" and env in allowed_envs

            if use_oauth:
                with open("/snowflake/session/token", "r") as token_file:
                    oauth_token = token_file.read().strip()

                session_config = {
                    "account": connection_params["account"],
                    "authenticator": "oauth",
                    "token": oauth_token,
                    "warehouse": connection_params["warehouse"],
                    "database": connection_params["database"],
                    "schema": connection_params["schema"],
                }

                if connection_params.get("role"):
                    session_config["role"] = connection_params["role"]

                self._session = Session.builder.configs(session_config).create()
            else:
                # Use private key authentication (same as database connection)
                import os

                from cryptography.hazmat.backends import default_backend
                from cryptography.hazmat.primitives import serialization

                # Get private key
                private_key_raw = getattr(
                    self.settings, "snowflake_private_key_raw", None
                )
                private_key_path = getattr(
                    self.settings, "snowflake_private_key_path", None
                )

                if private_key_raw:
                    # GitHub Actions case - key is provided as content
                    if not private_key_raw.startswith("-----BEGIN"):
                        if os.path.exists(private_key_raw):
                            with open(private_key_raw, "rb") as key:
                                key_data = key.read()
                        else:
                            key_data = private_key_raw.encode()
                    else:
                        key_data = private_key_raw.encode()
                elif private_key_path and os.path.exists(private_key_path):
                    with open(private_key_path, "rb") as key:
                        key_data = key.read()
                else:
                    raise HTTPException(
                        status_code=500,
                        detail="No valid private key found. Set either SNOWFLAKE_PRIVATE_KEY_RAW or SNOWFLAKE_PRIVATE_KEY_PATH",
                    )

                # Load private key
                passphrase = getattr(
                    self.settings, "snowflake_privatekey_password", None
                )
                password_bytes = passphrase.encode() if passphrase else None

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

                session_config = {
                    "account": connection_params["account"],
                    "user": connection_params["user"],
                    "warehouse": connection_params["warehouse"],
                    "database": connection_params["database"],
                    "schema": connection_params["schema"],
                    "authenticator": "snowflake",
                }

                if connection_params.get("role"):
                    session_config["role"] = connection_params["role"]

                # Use connector for private key authentication
                conn_config = {
                    "account": connection_params["account"],
                    "user": connection_params["user"],
                    "warehouse": connection_params["warehouse"],
                    "database": connection_params["database"],
                    "schema": connection_params["schema"],
                    "authenticator": "snowflake",
                    "private_key": pkb,
                }

                if connection_params.get("role"):
                    conn_config["role"] = connection_params["role"]

                # Create connection first, then session
                conn = connect(**conn_config)
                self._session = Session.builder.configs({"connection": conn}).create()

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to connect to Snowflake: {str(e)}"
            )

    def close(self):
        """Close Snowflake session and reset state"""
        if self._session:
            try:
                self._session.close()
            except:
                pass
            finally:
                self._session = None
                self._root = None
                self._connection_params = None
                self._service_metadata = {}

    def get_service_metadata(
        self, service_name: str, connection_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get metadata for a specific search service.
        Since we don't have permissions to SHOW CORTEX SEARCH SERVICES,
        we'll try to get metadata for the specific service directly.

        Args:
            service_name: Name of the search service
            connection_params: Optional dictionary to override connection parameters

        Returns:
            Dictionary containing service metadata
        """
        # Initialize metadata if empty
        if not self._service_metadata:
            self._load_services_metadata(connection_params)

        # Case-insensitive search for the service in cache
        service_name_lower = service_name.lower()

        # First try exact match
        if service_name in self._service_metadata:
            return self._service_metadata[service_name]

        # Then try lowercase match
        if service_name_lower in self._service_metadata:
            return self._service_metadata[service_name_lower]

        # If not in cache, try to load metadata for this specific service
        try:
            # Use BlendX Hub defaults if no connection_params provided
            if not connection_params:
                connection_params = {
                    "database": self.settings.blendx_hub_database
                    or self.settings.snowflake_database,
                    "schema": self.settings.blendx_hub_schema
                    or self.settings.snowflake_schema,
                }

            session = self.get_session(connection_params)

            # Switch context to the specified database/schema
            database = connection_params.get("database")
            schema = connection_params.get("schema")
            if database and schema:
                session.sql(f"USE DATABASE {database}").collect()
                session.sql(f"USE SCHEMA {schema}").collect()

            # Try to get metadata for the specific service
            # We'll try both the original name and common case variations
            service_variations = [
                service_name,
                service_name.upper(),
                service_name.lower(),
                service_name.title(),
            ]

            for svc_name in service_variations:
                try:
                    svc_details = session.sql(
                        f"DESC CORTEX SEARCH SERVICE {svc_name};"
                    ).collect()

                    search_column = next(
                        (
                            item["search_column"]
                            for item in svc_details
                            if "search_column" in item
                        ),
                        "CONTENT",  # Default search column
                    )

                    # Store in cache
                    metadata = {
                        "search_column": search_column,
                        "original_name": svc_name,
                    }

                    self._service_metadata[svc_name] = metadata
                    self._service_metadata[svc_name.lower()] = metadata

                    return metadata

                except Exception:
                    # Try next variation
                    continue

            # If none of the variations worked, the service doesn't exist
            raise HTTPException(
                status_code=400,
                detail=f"Service '{service_name}' not found. Tried variations: {service_variations}",
            )

        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Service '{service_name}' not found: {str(e)}",
            )

    def _load_services_metadata(
        self, connection_params: Optional[Dict[str, Any]] = None
    ):
        """
        Load metadata for all available search services.
        Since we don't have permissions to SHOW CORTEX SEARCH SERVICES,
        we'll load metadata on-demand when services are requested.

        Args:
            connection_params: Optional dictionary to override connection parameters
        """
        # Initialize empty metadata - we'll load services on-demand
        self._service_metadata = {}

    def get_available_services(
        self, connection_params: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Get list of available search services.

        Args:
            connection_params: Optional dictionary to override connection parameters

        Returns:
            List of available service names
        """
        if not self._service_metadata:
            self._load_services_metadata(connection_params)
        return list(self._service_metadata.keys())

    def test_connection(
        self, connection_params: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Test connection to Snowflake without storing the session.

        Args:
            connection_params: Optional dictionary to override connection parameters

        Returns:
            True if connection successful, False otherwise
        """
        try:
            test_params = self._get_connection_params(connection_params)

            # Use the same authentication logic as the main connection
            auth_method = (self.settings.snowflake_authmethod or "").lower()
            env = self.settings.environment.upper()
            allowed_envs = {"DEVELOPMENT", "SHARED", "STAGING", "PRODUCTION", "UAT"}
            use_oauth = auth_method == "oauth" and env in allowed_envs

            if use_oauth:
                with open("/snowflake/session/token", "r") as token_file:
                    oauth_token = token_file.read().strip()

                test_session = Session.builder.configs(
                    {
                        "account": test_params["account"],
                        "authenticator": "oauth",
                        "token": oauth_token,
                        "warehouse": test_params["warehouse"],
                        "database": test_params["database"],
                        "schema": test_params["schema"],
                        "role": test_params.get("role"),
                    }
                ).create()
            else:
                # Use private key authentication (same as database connection)
                import os

                from cryptography.hazmat.backends import default_backend
                from cryptography.hazmat.primitives import serialization

                # Get private key
                private_key_raw = getattr(
                    self.settings, "snowflake_private_key_raw", None
                )
                private_key_path = getattr(
                    self.settings, "snowflake_private_key_path", None
                )

                if private_key_raw:
                    if not private_key_raw.startswith("-----BEGIN"):
                        if os.path.exists(private_key_raw):
                            with open(private_key_raw, "rb") as key:
                                key_data = key.read()
                        else:
                            key_data = private_key_raw.encode()
                    else:
                        key_data = private_key_raw.encode()
                elif private_key_path and os.path.exists(private_key_path):
                    with open(private_key_path, "rb") as key:
                        key_data = key.read()
                else:
                    print(
                        "No valid private key found. Set either SNOWFLAKE_PRIVATE_KEY_RAW or SNOWFLAKE_PRIVATE_KEY_PATH"
                    )
                    return False

                # Load private key
                passphrase = getattr(
                    self.settings, "snowflake_privatekey_password", None
                )
                password_bytes = passphrase.encode() if passphrase else None

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

                session_config = {
                    "account": test_params["account"],
                    "user": test_params["user"],
                    "warehouse": test_params["warehouse"],
                    "database": test_params["database"],
                    "schema": test_params["schema"],
                    "authenticator": "snowflake",
                }

                if test_params.get("role"):
                    session_config["role"] = test_params["role"]

                # Use connector for private key authentication
                conn_config = {
                    "account": test_params["account"],
                    "user": test_params["user"],
                    "warehouse": test_params["warehouse"],
                    "database": test_params["database"],
                    "schema": test_params["schema"],
                    "authenticator": "snowflake",
                    "private_key": pkb,
                }

                if test_params.get("role"):
                    conn_config["role"] = test_params["role"]

                # Create connection first, then session
                conn = connect(**conn_config)
                test_session = Session.builder.configs({"connection": conn}).create()

            # Test the connection with a simple query
            test_session.sql("SELECT 1").collect()
            test_session.close()
            return True

        except Exception as e:
            print(f"Connection test failed: {str(e)}")
            return False

    @property
    def session(self) -> Session:
        """
        Legacy property for backward compatibility.
        Use get_session() for new code.
        """
        return self.get_session()

    @property
    def root(self) -> Root:
        """
        Legacy property for backward compatibility.
        Use get_root() for new code.
        """
        return self.get_root()


# Global instance management - can be overridden by parameterized instances
_snowflake_service_instance = None


def get_snowflake_service(settings: Optional[Settings] = None) -> SnowflakeService:
    """
    Dependency to get SnowflakeService instance.

    Args:
        settings: Optional Settings instance. If None, uses global instance or creates new one.

    Returns:
        SnowflakeService instance
    """
    global _snowflake_service_instance

    # If settings provided, return new instance with those settings
    if settings is not None:
        return SnowflakeService(settings)

    # Otherwise use global instance (but don't connect until needed)
    if _snowflake_service_instance is None:
        _snowflake_service_instance = SnowflakeService(get_settings())
    return _snowflake_service_instance


def create_snowflake_service(settings: Settings) -> SnowflakeService:
    """
    Create a new SnowflakeService instance with specific settings.

    Args:
        settings: Settings instance to use

    Returns:
        New SnowflakeService instance
    """
    return SnowflakeService(settings)


def get_snowflake_session(
    settings: Optional[Settings] = None,
    connection_params: Optional[Dict[str, Any]] = None,
):
    """
    Get a direct Snowflake connection.

    Args:
        settings: Optional Settings instance
        connection_params: Optional dictionary to override connection parameters

    Returns:
        Snowflake connection
    """
    config = settings or get_settings()

    # Prepare base connection parameters
    conn_params = {
        "user": config.snowflake_user,
        "password": config.snowflake_password,
        "account": config.snowflake_account,
        "warehouse": config.snowflake_warehouse,
        "database": config.snowflake_database,
        "schema": config.snowflake_schema,
        "role": config.snowflake_role,
    }

    # Override with custom parameters if provided
    if connection_params:
        conn_params.update(connection_params)

    # Remove None values
    conn_params = {k: v for k, v in conn_params.items() if v is not None}

    conn = connect(**conn_params)
    return conn
