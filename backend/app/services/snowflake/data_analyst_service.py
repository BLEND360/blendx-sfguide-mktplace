import asyncio
import os
from typing import Any, Dict, List, Optional

import aiohttp
import pandas as pd
import snowflake.connector
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from fastapi import HTTPException

from app.config.logging_config import logger
from app.config.settings import Settings, get_settings


class DataAnalystService:
    def __init__(self, settings: Optional[Settings] = None):
        """Initialize Data Analyst service with settings"""
        self.settings = settings or get_settings()
        self._connector_session = None
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
            "host": self.settings.snowflake_host,
        }

        if override_params:
            base_params.update(override_params)

        # Remove None values
        return {k: v for k, v in base_params.items() if v is not None}

    def _connect_with_private_key(self, connection_params: Dict[str, Any]):
        """
        Connect to Snowflake using private key authentication.
        """
        logger.info("Using private key authentication")

        # Get private key
        private_key_raw = getattr(self.settings, "snowflake_private_key_raw", None)
        private_key_path = getattr(self.settings, "snowflake_private_key_path", None)

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
            raise HTTPException(
                status_code=500,
                detail="No valid private key found. Set either SNOWFLAKE_PRIVATE_KEY_RAW or SNOWFLAKE_PRIVATE_KEY_PATH",
            )

        passphrase = getattr(self.settings, "snowflake_privatekey_password", None)
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

        conn_config = {
            "user": connection_params["user"],
            "account": connection_params["account"],
            "warehouse": connection_params["warehouse"],
            "database": connection_params.get("database"),
            "schema": connection_params.get("schema"),
            "role": connection_params.get("role"),
            "host": connection_params.get("host"),
            "port": 443,
            "authenticator": "snowflake",
            "private_key": pkb,
        }

        # Remove None values
        conn_config = {k: v for k, v in conn_config.items() if v is not None}

        self._connector_session = snowflake.connector.connect(**conn_config)

    def _test_private_key_connection(self, connection_params: Dict[str, Any]):
        """
        Test private key connection without storing it.
        """
        # Get private key
        private_key_raw = getattr(self.settings, "snowflake_private_key_raw", None)
        private_key_path = getattr(self.settings, "snowflake_private_key_path", None)

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
            raise Exception("No valid private key found")

        passphrase = getattr(self.settings, "snowflake_privatekey_password", None)
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

        conn_config = {
            "user": connection_params["user"],
            "account": connection_params["account"],
            "warehouse": connection_params["warehouse"],
            "database": connection_params.get("database"),
            "schema": connection_params.get("schema"),
            "role": connection_params.get("role"),
            "host": connection_params.get("host"),
            "port": 443,
            "authenticator": "snowflake",
            "private_key": pkb,
        }

        # Remove None values
        conn_config = {k: v for k, v in conn_config.items() if v is not None}

        # Test the connection
        test_conn = snowflake.connector.connect(**conn_config)
        test_conn.cursor().execute("SELECT 1").fetchall()
        test_conn.close()

    def get_connection(self, connection_params: Optional[Dict[str, Any]] = None):
        """
        Get or create Snowflake connection with optional parameter overrides.

        Args:
            connection_params: Optional dictionary to override connection parameters

        Returns:
            Snowflake connection
        """
        # Check if we need to recreate connection due to parameter changes
        current_params = self._get_connection_params(connection_params)

        if self._connector_session is None or self._connection_params != current_params:
            self._connect_to_snowflake(current_params)
            self._connection_params = current_params

        return self._connector_session

    def _connect_to_snowflake(self, connection_params: Dict[str, Any]):
        """
        Establishes connection to Snowflake using appropriate authentication method.

        Args:
            connection_params: Dictionary containing connection parameters
        """
        logger.info("Connecting to Snowflake")

        try:
            # Close existing connection if any
            if self._connector_session:
                self.close()

            # Check authentication method first (priority over environment)
            auth_method = getattr(self.settings, "snowflake_authmethod", None)

            if auth_method == "private_key":
                logger.info("Using private key for authentication")
                self._connect_with_private_key(connection_params)
            elif self.settings.environment.upper() in [
                "DEVELOPMENT",
                "SHARED",
                "STAGING",
                "PRODUCTION",
                "UAT",
            ]:
                logger.info("Using OAuth token for authentication")
                with open("/snowflake/session/token", "r") as token_file:
                    oauth_token = token_file.read().strip()

                conn_config = {
                    "account": connection_params["account"],
                    "host": connection_params["host"],
                    "port": 443,
                    "warehouse": connection_params["warehouse"],
                    "authenticator": "oauth",
                    "token": oauth_token,
                }

                if connection_params.get("role"):
                    conn_config["role"] = connection_params["role"]

                self._connector_session = snowflake.connector.connect(**conn_config)
            else:
                logger.info("Using username and password for authentication")

                conn_config = {
                    "user": connection_params["user"],
                    "password": connection_params["password"],
                    "account": connection_params["account"],
                    "host": connection_params["host"],
                    "port": 443,
                    "warehouse": connection_params["warehouse"],
                }

                if connection_params.get("role"):
                    conn_config["role"] = connection_params["role"]

                self._connector_session = snowflake.connector.connect(**conn_config)

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to connect to Snowflake: {str(e)}"
            )

    def close(self):
        """Close Snowflake connection and reset state"""
        if self._connector_session:
            try:
                self._connector_session.close()
            except:
                pass
            finally:
                self._connector_session = None
                self._connection_params = None

    async def ask_question(
        self,
        query: str,
        semantic_model_path: str,
        connection_params: Optional[Dict[str, Any]] = None,
    ):
        """
        Ask a natural language question to Snowflake Cortex Analyst

        Args:
            query: Natural language question
            semantic_model_path: Path to the semantic model file
            connection_params: Optional dictionary to override connection parameters
        """
        logger.info("Asking question: %s", query)
        try:
            # Get connection with dynamic parameters
            connection = self.get_connection(connection_params)
            connector_token = connection.rest.token

            response = await self.send_message(
                prompt=query,
                token=connector_token,
                semantic_model_path=semantic_model_path,
                connection_params=connection_params,
            )

            generated_query = None
            data = None

            for item in response["message"]["content"]:
                if item["type"] == "sql":
                    generated_query = item["statement"]
                    data = await self.execute_sql(generated_query, connection_params)

            # Return both the SQL query and the data
            return {"sql_query": generated_query, "data": data}
        except Exception as e:
            logger.error("Error in ask_question: %s", str(e))
            raise HTTPException(
                status_code=500, detail=f"Analyst question failed: {str(e)}"
            )

    async def send_message(
        self,
        prompt: str,
        token: str,
        semantic_model_path: str,
        connection_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Calls the REST API and returns the response.

        Args:
            prompt: Natural language prompt
            token: Authentication token
            semantic_model_path: Path to semantic model
            connection_params: Optional connection parameters for host override
        """
        logger.debug("Sending message to Cortex Analyst API")

        # Use connection params for host if provided, otherwise use settings
        current_params = self._get_connection_params(connection_params)
        host = current_params["host"]

        logger.debug(f"Using semantic model path: {semantic_model_path}")

        request_body = {
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": prompt}]}
            ],
            "semantic_model_file": semantic_model_path,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url=f"https://{host}/api/v2/cortex/analyst/message",
                json=request_body,
                headers={
                    "Authorization": f'Snowflake Token="{token}"',
                    "Content-Type": "application/json",
                },
            ) as resp:
                request_id = resp.headers.get("X-Snowflake-Request-Id")
                if resp.status < 400:
                    return {**(await resp.json()), "request_id": request_id}
                else:
                    logger.error(
                        "Failed request (id: %s) with status %s: %s",
                        request_id,
                        resp.status,
                        await resp.text(),
                    )
                    raise Exception(
                        f"Failed request (id: {request_id}) with status {resp.status}: {await resp.text()}"
                    )

    async def execute_sql(
        self, query: str, connection_params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute SQL query asynchronously

        Args:
            query: SQL query to execute
            connection_params: Optional connection parameters
        """
        logger.debug("Executing SQL query: %s", query)
        try:
            # Get connection with dynamic parameters
            connection = self.get_connection(connection_params)

            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(
                None,
                lambda: pd.DataFrame(connection.cursor().execute(query).fetchall()),
            )

            if not df.empty and connection.cursor().description:
                columns = [col[0] for col in connection.cursor().description]
                df.columns = columns

            return df.to_dict(orient="records")
        except Exception as e:
            logger.error("SQL execution failed: %s", str(e))
            raise HTTPException(
                status_code=500, detail=f"SQL execution failed: {str(e)}"
            )

    async def generate_nl_summary(
        self,
        question: str,
        data: List[Dict[str, Any]],
        llm_config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate a natural language summary using the LLM

        Args:
            question: Original question
            data: Data to summarize
            llm_config: Optional LLM configuration
        """
        logger.info("Generating natural language summary for question: %s", question)
        if not data:
            return "No data available to generate a summary."

        # Use provided LLM config or fall back to settings
        llm_settings = llm_config or {
            "api_key": getattr(self.settings, "llm_api_key", None),
            "model_name": getattr(self.settings, "llm_model_name", "gpt-3.5-turbo"),
            "api_url": "https://api.openai.com/v1/chat/completions",
        }

        data_str = "\n".join(
            [
                ", ".join([f"{key}: {value}" for key, value in row.items()])
                for row in data
            ]
        )
        prompt = f"Based on the following data, provide a summary for the question: {question}\n\nData:\n{data_str}"

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url=llm_settings["api_url"],
                headers={
                    "Authorization": f"Bearer {llm_settings['api_key']}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": llm_settings["model_name"],
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 150,
                    "temperature": 0.7,
                },
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["choices"][0]["message"]["content"].strip()
                else:
                    logger.error("LLM request failed: %s", await response.text())
                    raise HTTPException(
                        status_code=500,
                        detail=f"LLM request failed: {await response.text()}",
                    )

    def test_connection(
        self, connection_params: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Test connection to Snowflake without storing the connection.

        Args:
            connection_params: Optional dictionary to override connection parameters

        Returns:
            True if connection successful, False otherwise
        """
        try:
            test_params = self._get_connection_params(connection_params)

            # Check authentication method first (priority over environment)
            auth_method = getattr(self.settings, "snowflake_authmethod", None)

            if auth_method == "private_key":
                # Test private key connection
                self._test_private_key_connection(test_params)
                return True
            elif self.settings.environment.upper() in [
                "DEVELOPMENT",
                "SHARED",
                "STAGING",
                "PRODUCTION",
                "UAT",
            ]:
                with open("/snowflake/session/token", "r") as token_file:
                    oauth_token = token_file.read().strip()

                test_conn = snowflake.connector.connect(
                    account=test_params["account"],
                    host=test_params["host"],
                    port=443,
                    warehouse=test_params["warehouse"],
                    role=test_params.get("role"),
                    authenticator="oauth",
                    token=oauth_token,
                )
            else:
                test_conn = snowflake.connector.connect(
                    user=test_params["user"],
                    password=test_params["password"],
                    account=test_params["account"],
                    host=test_params["host"],
                    port=443,
                    warehouse=test_params["warehouse"],
                    role=test_params.get("role"),
                )

            # Test the connection with a simple query
            test_conn.cursor().execute("SELECT 1").fetchall()
            test_conn.close()
            return True

        except Exception as e:
            print(f"Connection test failed: {str(e)}")
            return False


# Global instance management - can be overridden by parameterized instances
_data_analyst_service_instance = None


def get_data_analyst_service(settings: Optional[Settings] = None) -> DataAnalystService:
    """
    Dependency to get DataAnalystService instance.

    Args:
        settings: Optional Settings instance. If None, uses global instance or creates new one.

    Returns:
        DataAnalystService instance
    """
    global _data_analyst_service_instance

    # If settings provided, return new instance with those settings
    if settings is not None:
        return DataAnalystService(settings)

    # Otherwise use global instance (but don't connect until needed)
    if _data_analyst_service_instance is None:
        _data_analyst_service_instance = DataAnalystService(get_settings())
    return _data_analyst_service_instance


def create_data_analyst_service(settings: Settings) -> DataAnalystService:
    """
    Create a new DataAnalystService instance with specific settings.

    Args:
        settings: Settings instance to use

    Returns:
        New DataAnalystService instance
    """
    return DataAnalystService(settings)
