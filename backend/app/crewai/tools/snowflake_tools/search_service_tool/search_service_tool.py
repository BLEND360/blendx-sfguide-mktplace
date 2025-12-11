"""
Async-Compatible Search Service Tool

Base class for SearchService tools. Instances are created via the factory from BlendX Hub.
"""

import asyncio
import concurrent.futures
import logging
import threading
from typing import Any, Dict, List

from crewai.tools import BaseTool
from pydantic import PrivateAttr

from app.config.settings import get_settings
from app.services.snowflake.search_service import get_search_service
from app.services.snowflake.snowflake_service import get_snowflake_service

logger = logging.getLogger(__name__)


class SnowflakeToolSetupException(Exception):
    pass


class SearchService(BaseTool):
    """Base tool for vector search in Snowflake Search Service - Async Compatible.

    Note: This is a base class. Instances should be created via SnowflakeToolFactory
    which configures them from BlendX Hub.
    """

    name: str = "SearchService"
    description: str = ""

    # Use PrivateAttr for internal attributes that shouldn't be part of the schema
    _settings = PrivateAttr()
    _search_service = PrivateAttr()
    _snowflake_service = PrivateAttr()
    _config = PrivateAttr()

    def __init__(self, timeout=60):
        """
        Initialize the tool with services.

        Args:
            timeout: Tool timeout in seconds
        """
        super().__init__(timeout=timeout)
        self._search_service = get_search_service()
        self._snowflake_service = get_snowflake_service()
        self._settings = get_settings()
        self._config = {}

        logger.info(f"Initialized SearchService tool: {self.name}")

    def _get_search_config(self) -> Dict[str, Any]:
        """Get search configuration from BlendX Hub settings."""
        search_config = self._config.get("search", {})

        # Check if this is a BlendX Hub service (has hub_metadata)
        is_blendx_hub_service = "hub_metadata" in self._config

        if is_blendx_hub_service:
            # For BlendX Hub services, use BlendX Hub settings as defaults
            logger.info("Using BlendX Hub service configuration")
            config = {
                "service_name": self.name,
                "num_results": search_config.get("num_results", 5),
                "fields": search_config.get("fields", []),
                "filter_mapping": search_config.get("filter_mapping", {}),
                "database": (
                    self._settings.blendx_hub_database
                    or self._settings.snowflake_database
                ),
                "schema": (
                    self._settings.blendx_hub_schema or self._settings.snowflake_schema
                ),
                "warehouse": (
                    self._settings.blendx_hub_warehouse
                    or self._settings.snowflake_warehouse
                ),
                "role": self._settings.snowflake_role,
            }
        else:
            # Fallback to default settings
            logger.info("Using default Snowflake configuration")
            config = {
                "service_name": self._settings.snowflake_search_service_name,
                "num_results": 5,
                "fields": [],
                "filter_mapping": {},
                "database": self._settings.snowflake_database,
                "schema": self._settings.snowflake_schema,
                "warehouse": self._settings.snowflake_warehouse,
                "role": self._settings.snowflake_role,
            }

        logger.info(f"Final search configuration: {config}")

        return config

    def _run_async_in_new_loop(self, coro):
        """
        Run an async coroutine in a new event loop in a separate thread.
        This solves the "event loop already running" issue.
        """

        def run_in_thread():
            # Create a new event loop for this thread
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                return new_loop.run_until_complete(coro)
            finally:
                new_loop.close()

        # Run in a thread pool to avoid blocking
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_in_thread)
            return future.result()

    async def _run_async_safely(self, coro):
        """
        Run async coroutine safely, handling different event loop scenarios.
        """
        try:
            # Try to get current loop
            current_loop = asyncio.get_running_loop()
            logger.debug("Running in existing event loop")

            # If we're in an async context, we need to run in a thread
            # to avoid "event loop already running" error
            return await asyncio.get_event_loop().run_in_executor(
                None, lambda: self._run_async_in_new_loop(coro)
            )

        except RuntimeError:
            # No current event loop, safe to create one
            logger.debug("No current event loop, creating new one")
            return asyncio.run(coro)

    def _run(self, query: str) -> Dict[str, Any]:
        """
        Args:
            query: Natural language query to search for

        Returns:
            Dictionary containing search results
        """
        try:
            # Get search configuration with proper environment overrides
            search_config = self._get_search_config()

            # Validate required configuration
            if not search_config.get("service_name"):
                return {
                    "query": query,
                    "error": "Search service name not configured. Please configure via BlendX Hub.",
                }

            final_num_results = search_config["num_results"]
            enhanced_query = query

            if self._search_service and self._snowflake_service:
                # Prepare connection parameters
                connection_params = {
                    "database": search_config["database"],
                    "schema": search_config["schema"],
                    "warehouse": search_config["warehouse"],
                    "role": search_config["role"],
                }

                # Remove None values
                connection_params = {
                    k: v for k, v in connection_params.items() if v is not None
                }

                logger.info(f"Using connection parameters: {connection_params}")

                # Create the coroutine
                search_coro = self._search_service.query_cortex_search_service(
                    snowflake_service=self._snowflake_service,
                    query=enhanced_query,
                    service_name=search_config["service_name"],
                    num_chunks=final_num_results,
                    db=search_config["database"],
                    schema=search_config["schema"],
                    fields=search_config["fields"] or [],
                    connection_params=connection_params,
                )

                try:
                    # Check if we're in an async context
                    try:
                        current_loop = asyncio.get_running_loop()
                        # We're in an async context (like FastAPI), run in new thread
                        logger.debug(
                            "Detected running event loop, using thread executor"
                        )
                        search_results = self._run_async_in_new_loop(search_coro)
                    except RuntimeError:
                        # No running loop, safe to use asyncio.run
                        logger.debug("No running event loop, using asyncio.run")
                        search_results = asyncio.run(search_coro)

                except Exception as async_error:
                    logger.error(f"Async execution failed: {str(async_error)}")
                    return {
                        "query": query,
                        "error": f"Async execution failed: {str(async_error)}",
                    }

                # Convert results to dictionaries
                dict_results = self._convert_results_to_dicts(search_results)

                return {
                    "query": query,
                    "enhanced_query": enhanced_query,
                    "results": dict_results,
                    "result_count": len(dict_results),
                    "config_used": {
                        "service_name": search_config["service_name"],
                        "database": search_config["database"],
                        "schema": search_config["schema"],
                        "warehouse": search_config["warehouse"],
                        "role": search_config["role"],
                        "num_results": final_num_results,
                    },
                }
            else:
                return {
                    "query": query,
                    "error": "Search service or Snowflake service not available",
                }

        except Exception as e:
            logger.error(f"Error searching: {str(e)}", exc_info=True)
            return {"query": query, "error": f"Failed to search: {str(e)}"}

    def _convert_results_to_dicts(self, results: List[Any]) -> List[Dict[str, Any]]:
        """Convert search results to dictionaries."""
        dict_results = []

        for result in results:
            try:
                result_dict = {}

                if hasattr(result, "model_dump"):
                    result_dict = result.model_dump()
                elif hasattr(result, "dict"):
                    result_dict = result.dict()
                elif hasattr(result, "__dict__"):
                    result_dict = dict(result.__dict__)
                    result_dict = {
                        k: v for k, v in result_dict.items() if not k.startswith("_")
                    }
                elif isinstance(result, dict):
                    result_dict = dict(result)
                else:
                    result_dict = {"value": str(result), "type": str(type(result))}

                dict_results.append(result_dict)

            except Exception as e:
                logger.warning(f"Error converting result to dict: {str(e)}")
                dict_results.append(
                    {
                        "conversion_error": str(e),
                        "original_result": str(result),
                        "result_type": str(type(result)),
                    }
                )

        return dict_results

    def get_current_config(self) -> Dict[str, Any]:
        """Get the current effective configuration."""
        search_config = self._get_search_config()

        return {
            "tool_name": self.name,
            "tool_description": self.description,
            "search_config": search_config,
            "raw_config": self._config,
            "settings_defaults": {
                "snowflake_database": self._settings.snowflake_database,
                "snowflake_schema": self._settings.snowflake_schema,
                "snowflake_warehouse": self._settings.snowflake_warehouse,
                "snowflake_role": self._settings.snowflake_role,
                "snowflake_user": self._settings.snowflake_user,
                "snowflake_account": self._settings.snowflake_account,
                "blendx_hub_database": self._settings.blendx_hub_database,
                "blendx_hub_schema": self._settings.blendx_hub_schema,
                "blendx_hub_warehouse": self._settings.blendx_hub_warehouse,
            },
        }

    def validate_connection(self):
        """
        Validate the Snowflake connection and search service for this tool. Raise if not properly set up.
        """
        logger.info(f"🔍 Starting validation for SearchService tool: '{self.name}'")

        config = self._get_search_config()
        connection_params = {
            "database": config["database"],
            "schema": config["schema"],
            "warehouse": config["warehouse"],
            "role": config["role"],
        }

        logger.info(
            f"📊 Connection parameters for '{self.name}': database={connection_params['database']}, schema={connection_params['schema']}, warehouse={connection_params['warehouse']}, role={connection_params['role']}"
        )

        # First validate basic Snowflake connection
        logger.info(f"🔌 Testing basic Snowflake connectivity for '{self.name}'...")
        if not self._snowflake_service.test_connection(connection_params):
            logger.error(f"❌ Snowflake connection failed for tool '{self.name}'")
            raise SnowflakeToolSetupException(
                f"Snowflake SearchService '{self.name}' is not properly set up. Check credentials and environment variables."
            )
        logger.info(f"✅ Basic Snowflake connectivity validated for '{self.name}'")

        # Then validate that the specific search service exists
        try:
            service_name = config.get("service_name")
            if not service_name:
                logger.error(
                    f"❌ Search service name not configured for tool '{self.name}'"
                )
                raise SnowflakeToolSetupException(
                    f"Search service name not configured for tool '{self.name}'. Please configure via BlendX Hub."
                )

            logger.info(
                f"🔍 Validating search service '{service_name}' for tool '{self.name}'..."
            )

            # This will raise an exception if the service doesn't exist
            self._snowflake_service.get_service_metadata(
                service_name, connection_params
            )
            logger.info(
                f"✅ Search service '{service_name}' validated successfully for tool '{self.name}'"
            )

        except Exception as e:
            if "not found" in str(e):
                logger.error(
                    f"❌ Search service '{service_name}' not found for tool '{self.name}'"
                )
                # Get available services for better error message
                try:
                    logger.info(
                        f"📋 Retrieving available search services for tool '{self.name}'..."
                    )
                    available_services = self._snowflake_service.get_available_services(
                        connection_params
                    )
                    logger.info(f"📋 Available services: {available_services}")
                    raise SnowflakeToolSetupException(
                        f"Search service '{service_name}' not found for tool '{self.name}'. Available services: {available_services}"
                    )
                except Exception as list_error:
                    logger.error(
                        f"❌ Failed to retrieve available services: {str(list_error)}"
                    )
                    raise SnowflakeToolSetupException(
                        f"Search service '{service_name}' not found for tool '{self.name}'. Error: {str(e)}"
                    )
            else:
                logger.error(
                    f"❌ Failed to validate search service '{service_name}' for tool '{self.name}': {str(e)}"
                )
                raise SnowflakeToolSetupException(
                    f"Failed to validate search service '{service_name}' for tool '{self.name}'. Error: {str(e)}"
                )

        logger.info(
            f"🎉 Validation completed successfully for SearchService tool: '{self.name}'"
        )
