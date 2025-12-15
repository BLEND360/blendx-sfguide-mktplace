"""
Module for creating and managing Snowflake tools from BlendX Hub.
Supports dynamic instantiation and management of SearchService and DataAnalyst tools for CrewAI workflows.
"""

# Standard library imports
import asyncio
import concurrent.futures
import logging
import threading
from typing import Any, Dict, List, Type, Union

# Third-party library imports
from crewai.tools import BaseTool

logger = logging.getLogger(__name__)


class SnowflakeToolFactory:
    """Factory class to create multiple instances of Snowflake tools from BlendX Hub."""

    @staticmethod
    def create_all_tools(
        search_tool_names: List[str] = None,
        analyst_tool_names: List[str] = None,
    ) -> List[BaseTool]:
        """
        Create all tool instances from BlendX Hub.

        Args:
            search_tool_names: Optional list of SearchService tool names to create
            analyst_tool_names: Optional list of Data Analyst tool names to create

        Returns:
            List of instantiated tool objects
        """
        tools = []

        # # Create SearchServices from BlendX Hub
        # search_tools = SnowflakeToolFactory.create_search_services(
        #     tool_names=search_tool_names
        # )
        # tools.extend(search_tools)

        # # Create Data Analysts from BlendX Hub
        # analyst_tools = SnowflakeToolFactory.create_data_analysts(
        #     tool_names=analyst_tool_names
        # )
        # tools.extend(analyst_tools)

        logger.info(f"Total tools created: {len(tools)}")
        return tools

    @staticmethod
    def create_search_services(tool_names: List[str] = None) -> List[BaseTool]:
        """
        Create SearchService instances from BlendX Hub API.

        Args:
            tool_names: List of specific tool names to create. If None, creates all available.

        Returns:
            List of SearchService tool instances
        """
        from app.services.blendx_hub_search_service import get_blendx_hub_search_service

        tools = []
        hub_service = get_blendx_hub_search_service()

        try:
            # Fetch available search services from BlendX Hub
            available_services = hub_service.get_available_search_services()
            logger.info(
                f"Found {len(available_services)} search services in BlendX Hub"
            )

            # Filter by tool_names if specified
            if tool_names is not None:
                # Validate that requested services exist
                validation_results = hub_service.validate_search_services(tool_names)
                missing_services = [
                    name
                    for name, available in validation_results.items()
                    if not available
                ]

                if missing_services:
                    logger.warning(
                        f"Requested search services not found in BlendX Hub: {missing_services}"
                    )

                # Filter available services to only include requested ones
                available_services = [
                    service
                    for service in available_services
                    if service.get("service_name") in tool_names
                ]
                logger.info(f"Filtered to {len(available_services)} requested services")

            # Create tools for each available service
            for service_data in available_services:
                service_name = service_data.get("service_name", "Unnamed")

                try:
                    # Convert BlendX Hub service data to tool configuration
                    tool_config = SnowflakeToolFactory._convert_hub_service_to_config(
                        service_data
                    )

                    # Create a specific tool class for this service
                    tool_class = SnowflakeToolFactory._create_search_service_class(
                        service_name, tool_config
                    )
                    tool_instance = tool_class()
                    tools.append(tool_instance)
                    logger.info(f"Created SearchService tool: {service_name}")

                except Exception as e:
                    logger.error(
                        f"Failed to create SearchService tool '{service_name}': {str(e)}"
                    )

        except Exception as e:
            logger.error(f"Failed to fetch search services from BlendX Hub: {str(e)}")

        return tools

    @staticmethod
    def create_data_analysts(tool_names: List[str] = None) -> List[BaseTool]:
        """
        Create Data Analyst instances from BlendX Hub only.

        Args:
            tool_names: Optional list of specific tool names to create. If None, creates all.

        Returns:
            List of Data Analyst tool instances
        """
        tools = []

        try:
            import httpx

            from app.config.settings import get_settings

            settings = get_settings()
            base_url = settings.blendx_hub_url

            if not base_url:
                raise ValueError("BlendX Hub URL not configured")

            endpoint = f"{base_url}/cortex-data-analyst/analysts"

            with httpx.Client(timeout=30.0) as client:
                response = client.get(endpoint)
                response.raise_for_status()
                all_analysts = response.json()

                if not isinstance(all_analysts, list):
                    raise ValueError(
                        f"Expected list of analysts, got {type(all_analysts)}"
                    )

                # Filter only active analysts
                hub_analysts = [
                    analyst
                    for analyst in all_analysts
                    if analyst.get("status") == "ACTIVE"
                ]

            if hub_analysts:
                logger.info(
                    f"Found {len(hub_analysts)} active data analysts from BlendX Hub"
                )

                for analyst in hub_analysts:
                    analyst_name = analyst.get("data_analyst_name", "Unnamed")

                    # Filter by tool_names if specified
                    if tool_names is not None and analyst_name not in tool_names:
                        logger.info(
                            f"⏭️  Skipping '{analyst_name}' - not in requested list: {tool_names}"
                        )
                        continue

                    try:
                        # Create Hub-based tool configuration
                        # Use description from Hub if available, otherwise use default
                        hub_description = analyst.get(
                            "description",
                            f"Data analyst tool for {analyst_name} from BlendX Hub",
                        )
                        hub_config = {
                            "name": analyst_name,
                            "description": hub_description,
                            "analyst": {"max_results": 10},
                            "hub_metadata": {
                                "analyst_name": analyst_name,
                                "data_analyst_id": analyst.get("data_analyst_id"),
                                "stage_path": analyst.get("stage_path"),
                                "tables_referenced": analyst.get(
                                    "tables_referenced", []
                                ),
                                "status": analyst.get("status"),
                                "description": hub_description,
                            },
                        }

                        tool_class = SnowflakeToolFactory._create_analyst_tool_class(
                            hub_config
                        )
                        tool_instance = tool_class()
                        tools.append(tool_instance)
                        logger.info(f"Created Data Analyst tool: {analyst_name}")

                    except Exception as e:
                        logger.error(
                            f"Failed to create Data Analyst tool '{analyst_name}': {str(e)}"
                        )
            else:
                logger.warning("No active data analysts found in BlendX Hub")

        except Exception as e:
            logger.error(f"Failed to fetch data analysts from BlendX Hub: {e}")
            return tools

        return tools

    @staticmethod
    def _convert_hub_service_to_config(service_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert BlendX Hub service data to tool configuration format.

        Args:
            service_data: Service data from BlendX Hub API

        Returns:
            Tool configuration dictionary
        """
        from app.services.blendx_hub_search_service import get_blendx_hub_search_service

        hub_service = get_blendx_hub_search_service()

        # Parse the search service URL to extract database/schema info
        search_service_url = service_data.get("search_service_url", "")
        parsed_url = hub_service.parse_search_service_url(search_service_url)

        # Extract metadata columns for potential filtering
        metadata_columns = service_data.get("metadata_columns", {})

        # Create tool configuration
        config = {
            "name": service_data.get("service_name", "Unnamed"),
            "description": f"Search service: {service_data.get('service_name', 'Unnamed')} - {service_data.get('total_documents', 0)} documents, {service_data.get('total_chunks', 0)} chunks",
            "search": {
                "num_results": 5,  # Default number of results
                "fields": [],  # No specific fields by default
                "filter_mapping": {},  # No filter mapping by default
            },
            "hub_metadata": {
                "search_service_id": service_data.get("search_service_id"),
                "stage_name": service_data.get("stage_name"),
                "status": service_data.get("status"),
                "metadata_columns": metadata_columns,
                "total_documents": service_data.get("total_documents", 0),
                "total_chunks": service_data.get("total_chunks", 0),
                "created_at": service_data.get("created_at"),
                "updated_at": service_data.get("updated_at"),
            },
        }

        return config

    @staticmethod
    def _create_search_service_class(
        service_name: str, config: Dict[str, Any]
    ) -> Type[BaseTool]:
        """Create a SearchService class for a given service from BlendX Hub."""
        # Import here to avoid circular imports
        from app.config.settings import get_settings
        from app.crewai.tools.snowflake_tools.search_service_tool.search_service_tool import (
            SearchService,
        )
        from app.services.snowflake.search_service import get_search_service
        from app.services.snowflake.snowflake_service import get_snowflake_service

        class HubSearchService(SearchService):
            """SearchService configured from BlendX Hub."""

            def __init__(self, timeout=60):
                """Initialize with BlendX Hub configuration."""
                # Initialize the BaseTool first
                BaseTool.__init__(self, timeout=timeout)

                # Set up services
                self._search_service = get_search_service()
                self._snowflake_service = get_snowflake_service()
                self._settings = get_settings()

                # Use the provided config from BlendX Hub
                self._config = config

                # Set tool name and description from config
                self.name = service_name
                self.description = config.get(
                    "description", f"Search service for {service_name}"
                )

                logger.info(f"Initialized Hub SearchService tool: {self.name}")

            def _get_search_config(self) -> Dict[str, Any]:
                """Get search configuration from BlendX Hub settings."""
                search_config = self._config.get("search", {})

                config_result = {
                    "service_name": self.name,
                    "num_results": search_config.get("num_results", 5),
                    "fields": search_config.get("fields", []),
                    "filter_mapping": search_config.get("filter_mapping", {}),
                    "database": (
                        self._settings.blendx_hub_database
                        or self._settings.snowflake_database
                    ),
                    "schema": (
                        self._settings.blendx_hub_schema
                        or self._settings.snowflake_schema
                    ),
                    "warehouse": (
                        self._settings.blendx_hub_warehouse
                        or self._settings.snowflake_warehouse
                    ),
                    "role": self._settings.snowflake_role,
                    "user": self._settings.snowflake_user,
                    "password": self._settings.snowflake_password,
                    "account": self._settings.snowflake_account,
                }

                # Log the final configuration (with sensitive data masked)
                masked_config = config_result.copy()
                masked_config["password"] = (
                    "***MASKED***" if config_result["password"] else None
                )
                logger.info(
                    f"Final search configuration for {self.name}: {masked_config}"
                )

                return config_result

            def _run_async_safely(self, coro):
                """
                Run async coroutine safely in any context.
                This method handles all possible event loop scenarios.
                """
                try:
                    # Method 1: Try to get current loop
                    try:
                        current_loop = asyncio.get_running_loop()
                        logger.debug(
                            f"Found running event loop in thread: {threading.current_thread().name}"
                        )

                        # We're in an async context, need to run in a separate thread
                        return self._run_in_new_thread_with_loop(coro)

                    except RuntimeError:
                        # Method 2: No current loop, try to get the event loop for this thread
                        logger.debug(
                            f"No running event loop in thread: {threading.current_thread().name}"
                        )

                        try:
                            # Try to get the event loop for this thread (might be set but not running)
                            loop = asyncio.get_event_loop()
                            if loop.is_running():
                                # Loop exists but is running, use thread approach
                                return self._run_in_new_thread_with_loop(coro)
                            else:
                                # Loop exists but not running, we can use it
                                return loop.run_until_complete(coro)
                        except RuntimeError:
                            # Method 3: No event loop at all, create new one
                            logger.debug("No event loop found, creating new one")
                            return asyncio.run(coro)

                except Exception as e:
                    # Method 4: Fallback - always use new thread approach
                    logger.warning(
                        f"Async detection failed: {str(e)}, using fallback method"
                    )
                    return self._run_in_new_thread_with_loop(coro)

            def _run_in_new_thread_with_loop(self, coro):
                """
                Run coroutine in a completely new thread with its own event loop.
                This is the most reliable method for avoiding conflicts.
                """

                def run_in_thread():
                    # Create a completely new event loop
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        logger.debug(
                            f"Created new event loop in thread: {threading.current_thread().name}"
                        )
                        return new_loop.run_until_complete(coro)
                    finally:
                        # Always clean up the loop
                        new_loop.close()
                        asyncio.set_event_loop(None)

                # Use thread pool executor for maximum isolation
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(run_in_thread)
                    return future.result()

            def _run(self, query: str) -> Dict[str, Any]:
                """
                Search using Snowflake SearchService with proper async handling for all contexts.

                Args:
                    query: Natural language query to search for

                Returns:
                    Dictionary containing search results
                """
                try:
                    # Get search configuration - all parameters come from config
                    search_config = self._get_search_config()

                    # Validate required configuration
                    if not search_config.get("service_name"):
                        return {
                            "query": query,
                            "error": f"Search service name not configured for tool '{self.name}'.",
                        }

                    # Use configuration values directly
                    final_num_results = search_config["num_results"]
                    enhanced_query = query

                    if self._search_service and self._snowflake_service:
                        # Prepare connection parameters for dynamic connection
                        connection_params = {
                            "database": search_config["database"],
                            "schema": search_config["schema"],
                            "warehouse": search_config["warehouse"],
                            "role": search_config["role"],
                            "user": search_config["user"],
                            "password": search_config["password"],
                            "account": search_config["account"],
                        }

                        # Remove None values from connection params
                        connection_params = {
                            k: v for k, v in connection_params.items() if v is not None
                        }

                        # Log connection parameters (with sensitive data masked)
                        masked_params = connection_params.copy()
                        if "password" in masked_params:
                            masked_params["password"] = "***MASKED***"
                        logger.info(
                            f"Using connection parameters for {self.name}: {masked_params}"
                        )

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

                        # Handle async execution safely in all contexts
                        try:
                            search_results = self._run_async_safely(search_coro)
                        except Exception as async_error:
                            logger.error(
                                f"Async execution failed for {self.name}: {str(async_error)}",
                                exc_info=True,
                            )
                            return {
                                "query": query,
                                "error": f"Async execution failed: {str(async_error)}",
                            }

                        # Convert all results to dictionaries
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
                    logger.error(
                        f"Error searching with tool {self.name}: {str(e)}",
                        exc_info=True,
                    )
                    return {"query": query, "error": f"Failed to search: {str(e)}"}

            def _convert_results_to_dicts(self, results):
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
                                k: v
                                for k, v in result_dict.items()
                                if not k.startswith("_")
                            }
                        elif isinstance(result, dict):
                            result_dict = dict(result)
                        else:
                            result_dict = {
                                "value": str(result),
                                "type": str(type(result)),
                            }

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
                """
                Get the current effective configuration (useful for debugging).
                """
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

        return HubSearchService

    @staticmethod
    def _create_analyst_tool_class(config: Dict[str, Any]) -> Type[BaseTool]:
        """Create a dynamic AnalystTool class with the provided configuration from BlendX Hub."""
        # Import here to avoid circular imports
        from app.config.settings import get_settings
        from app.crewai.tools.snowflake_tools.data_analyst_tool.data_analyst_tool import (
            AnalystTool,
            AnalystToolInput,
        )
        from app.services.snowflake.data_analyst_service import get_data_analyst_service

        class HubAnalystTool(AnalystTool):
            """AnalystTool configured from BlendX Hub."""

            def __init__(self, timeout=60, result_as_answer=True):
                """Initialize with BlendX Hub configuration."""
                # Initialize the BaseTool first with result_as_answer=True to force tool output
                BaseTool.__init__(
                    self, timeout=timeout, result_as_answer=result_as_answer
                )

                # Set up services with proper configuration
                self._settings = get_settings()
                self._data_analyst_service = get_data_analyst_service(self._settings)

                # Use the provided config from BlendX Hub
                self._config = config

                # Set tool name and description from config
                self.name = config.get("name", "AnalystTool")
                self.description = config.get(
                    "description", "Analyze data using Snowflake Cortex Analyst"
                )

                # Set the args schema
                self.args_schema = AnalystToolInput

                logger.info(
                    f"Initialized Hub AnalystTool: {self.name} (result_as_answer={result_as_answer})"
                )

            def _convert_dict_to_query(self, query_dict: dict) -> str:
                """
                Convert a dictionary of campaign parameters to a natural language query.

                Args:
                    query_dict: Dictionary containing campaign parameters

                Returns:
                    Natural language query string
                """
                query_parts = []

                # Campaign type
                if (
                    "campaign_type" in query_dict
                    and query_dict["campaign_type"] != "all"
                ):
                    query_parts.append(f"campaign type: {query_dict['campaign_type']}")

                # Duration
                if "duration" in query_dict:
                    query_parts.append(f"duration: {query_dict['duration']}")

                # Metrics
                if "metrics" in query_dict and query_dict["metrics"]:
                    metrics_str = ", ".join(query_dict["metrics"])
                    query_parts.append(f"metrics: {metrics_str}")

                # Demographics
                if "demographics" in query_dict and query_dict["demographics"]:
                    demo_str = ", ".join(query_dict["demographics"])
                    query_parts.append(f"demographics: {demo_str}")

                # Geographic locations
                if (
                    "geographic_locations" in query_dict
                    and query_dict["geographic_locations"]
                ):
                    geo_str = ", ".join(query_dict["geographic_locations"])
                    query_parts.append(f"locations: {geo_str}")

                # Languages
                if "languages" in query_dict and query_dict["languages"]:
                    lang_str = ", ".join(query_dict["languages"])
                    query_parts.append(f"languages: {lang_str}")

                # Build the query
                if query_parts:
                    base_query = "Analyze marketing campaign performance data"
                    filters = " with filters: " + ", ".join(query_parts)
                    return base_query + filters
                else:
                    return "Analyze marketing campaign performance data"

            def _get_analyst_config(self) -> Dict[str, Any]:
                """Get analyst configuration from BlendX Hub settings."""
                analyst_config = self._config.get("analyst", {})

                config_result = {
                    "max_results": analyst_config.get("max_results", 10),
                    "database": (
                        self._settings.blendx_hub_database
                        or self._settings.snowflake_database
                    ),
                    "schema": (
                        self._settings.blendx_hub_schema
                        or self._settings.snowflake_schema
                    ),
                    "warehouse": (
                        self._settings.blendx_hub_warehouse
                        or self._settings.snowflake_warehouse
                    ),
                    "role": self._settings.snowflake_role,
                    "user": self._settings.snowflake_user,
                    "password": self._settings.snowflake_password,
                    "account": self._settings.snowflake_account,
                }

                # Log the final configuration (with sensitive data masked)
                masked_config = config_result.copy()
                masked_config["password"] = (
                    "***MASKED***" if config_result["password"] else None
                )
                logger.info(
                    f"Final analyst configuration for {self.name}: {masked_config}"
                )

                return config_result

            def _build_semantic_model_path(self, analyst_config: Dict[str, Any]) -> str:
                """Build semantic model path from hub_metadata."""
                # Get stage_path from hub_metadata
                hub_metadata = self._config.get("hub_metadata", {})
                stage_path = hub_metadata.get("stage_path")
                if stage_path:
                    logger.info(f"✅ Using stage_path from hub_metadata: {stage_path}")
                    return stage_path

                logger.error("❌ No stage_path found in hub_metadata")
                return ""

            def _run_async_safely(self, coro):
                """Run async coroutine safely in any context."""
                try:
                    try:
                        current_loop = asyncio.get_running_loop()
                        logger.debug(
                            f"Found running event loop in thread: {threading.current_thread().name}"
                        )
                        return self._run_in_new_thread_with_loop(coro)
                    except RuntimeError:
                        logger.debug(
                            f"No running event loop in thread: {threading.current_thread().name}"
                        )
                        try:
                            loop = asyncio.get_event_loop()
                            if loop.is_running():
                                return self._run_in_new_thread_with_loop(coro)
                            else:
                                return loop.run_until_complete(coro)
                        except RuntimeError:
                            logger.debug("No event loop found, creating new one")
                            return asyncio.run(coro)
                except Exception as e:
                    logger.warning(
                        f"Async detection failed: {str(e)}, using fallback method"
                    )
                    return self._run_in_new_thread_with_loop(coro)

            def _run_in_new_thread_with_loop(self, coro):
                """Run coroutine in a completely new thread with its own event loop."""

                def run_in_thread():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        logger.debug(
                            f"Created new event loop in thread: {threading.current_thread().name}"
                        )
                        return new_loop.run_until_complete(coro)
                    finally:
                        new_loop.close()
                        asyncio.set_event_loop(None)

                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(run_in_thread)
                    return future.result()

            def _run(self, query: Union[str, dict]) -> Dict[str, Any]:
                """
                Analyze data using Snowflake Cortex Analyst with proper async handling for all contexts.

                Args:
                    query: Natural language query for analysis (string) or dictionary with campaign parameters

                Returns:
                    Dictionary containing analysis results
                """
                try:
                    # Convert dictionary to query string if needed
                    if isinstance(query, dict):
                        original_query = query
                        query = self._convert_dict_to_query(query)
                        logger.info(f"Converted dictionary to query: {query}")
                    else:
                        original_query = query

                    # Get analyst configuration - all parameters come from config
                    analyst_config = self._get_analyst_config()

                    # Build semantic model path from hub_metadata
                    final_semantic_model_path = self._build_semantic_model_path(
                        analyst_config
                    )
                    final_max_results = analyst_config["max_results"]

                    if not final_semantic_model_path:
                        return {
                            "query": query,
                            "error": "Semantic model path not found in BlendX Hub configuration.",
                        }

                    enhanced_query = query

                    if self._data_analyst_service:
                        # Prepare connection parameters for dynamic connection
                        connection_params = {
                            "database": analyst_config["database"],
                            "schema": analyst_config["schema"],
                            "warehouse": analyst_config["warehouse"],
                            "role": analyst_config["role"],
                            "user": analyst_config.get("user"),
                            "password": analyst_config.get("password"),
                            "account": analyst_config.get("account"),
                        }

                        # Remove None values from connection params
                        connection_params = {
                            k: v for k, v in connection_params.items() if v is not None
                        }

                        # Log connection parameters (masked)
                        masked_params = connection_params.copy()
                        if "password" in masked_params:
                            masked_params["password"] = "***MASKED***"
                        logger.info(
                            f"Using connection parameters for {self.name}: {masked_params}"
                        )
                        logger.info(
                            f"Using semantic model path: {final_semantic_model_path}"
                        )

                        # Create the coroutine
                        analysis_coro = self._data_analyst_service.ask_question(
                            query=enhanced_query,
                            semantic_model_path=final_semantic_model_path,
                            connection_params=connection_params,
                        )

                        # Handle async execution safely in all contexts
                        try:
                            result = self._run_async_safely(analysis_coro)
                        except Exception as async_error:
                            logger.error(
                                f"Async execution failed for {self.name}: {str(async_error)}",
                                exc_info=True,
                            )
                            return {
                                "query": query,
                                "original_query": original_query,
                                "error": f"Async execution failed: {str(async_error)}",
                            }

                        # Extract SQL query and data from the result
                        sql_query = (
                            result.get("sql_query")
                            if isinstance(result, dict)
                            else None
                        )
                        data = (
                            result.get("data") if isinstance(result, dict) else result
                        )

                        # Log the SQL query and response
                        if sql_query:
                            logger.info("🔧 GENERATED SQL QUERY:")
                            logger.info("=" * 50)
                            logger.info(sql_query)
                            logger.info("=" * 50)

                        if data:
                            logger.info(f"📊 QUERY RESPONSE:")
                            logger.info(
                                f"📈 Total items: {len(data) if isinstance(data, list) else 'N/A'}"
                            )
                            logger.info(
                                f"📋 Sample data: {data[:3] if isinstance(data, list) and len(data) > 0 else data}"
                            )

                        if data:
                            # Limit results
                            limited_data = (
                                data[:final_max_results]
                                if len(data) > final_max_results
                                else data
                            )

                            return {
                                "query": query,
                                "original_query": original_query,
                                "enhanced_query": enhanced_query,
                                "sql_query": sql_query,
                                "data": limited_data,
                                "total_items": len(data),
                                "returned_items": len(limited_data),
                                "config_used": {
                                    "semantic_model_path": final_semantic_model_path,
                                    "database": analyst_config["database"],
                                    "schema": analyst_config["schema"],
                                    "warehouse": analyst_config["warehouse"],
                                    "role": analyst_config["role"],
                                    "max_results": final_max_results,
                                },
                            }
                        else:
                            return {
                                "query": query,
                                "original_query": original_query,
                                "enhanced_query": enhanced_query,
                                "sql_query": sql_query,
                                "message": "No data found for the specified query.",
                                "config_used": {
                                    "semantic_model_path": final_semantic_model_path,
                                    "database": analyst_config["database"],
                                    "schema": analyst_config["schema"],
                                    "warehouse": analyst_config["warehouse"],
                                    "role": analyst_config["role"],
                                    "max_results": final_max_results,
                                },
                            }
                    else:
                        return {
                            "query": query,
                            "original_query": original_query,
                            "error": "Data Analyst service not available",
                        }

                except Exception as e:
                    logger.error(
                        f"Error analyzing data with tool {self.name}: {str(e)}",
                        exc_info=True,
                    )
                    return {
                        "query": query,
                        "original_query": (
                            original_query if "original_query" in locals() else query
                        ),
                        "error": f"Failed to analyze data: {str(e)}",
                    }

            def get_current_config(self) -> Dict[str, Any]:
                """Get the current effective configuration (useful for debugging)."""
                analyst_config = self._get_analyst_config()

                return {
                    "tool_name": self.name,
                    "tool_description": self.description,
                    "analyst_config": analyst_config,
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

        return HubAnalystTool


class SnowflakeToolsManager:
    """Manager class to handle multiple Snowflake tool instances."""

    def __init__(
        self,
        search_tool_names: List[str] = None,
        analyst_tool_names: List[str] = None,
    ):
        """
        Initialize the manager with tool instances from BlendX Hub.

        Args:
            search_tool_names: Optional list of SearchService tool names to create
            analyst_tool_names: Optional list of Data Analyst tool names to create
        """
        self.search_tool_names = search_tool_names
        self.analyst_tool_names = analyst_tool_names
        self.tools = SnowflakeToolFactory.create_all_tools(
            search_tool_names=search_tool_names,
            analyst_tool_names=analyst_tool_names,
        )

    def get_all_tools(self) -> List[BaseTool]:
        """Get all tool instances."""
        return self.tools

    def get_tools_by_type(self, tool_type: str) -> List[BaseTool]:
        """
        Get tools filtered by type.

        Args:
            tool_type: Type of tools to filter ('SearchService', 'AnalystTool')

        Returns:
            List of tools matching the specified type
        """
        return [
            tool
            for tool in self.tools
            if tool_type.lower() in tool.__class__.__name__.lower()
        ]

    def get_tool_by_name(self, name: str) -> BaseTool:
        """
        Get a specific tool by its name.

        Args:
            name: Name of the tool to retrieve

        Returns:
            Tool instance with the specified name, or None if not found
        """
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None

    def list_tool_names(self) -> List[str]:
        """Get list of all tool names."""
        return [tool.name for tool in self.tools]

    def reload_tools(self):
        """Reload all tools from BlendX Hub."""
        self.tools = SnowflakeToolFactory.create_all_tools(
            search_tool_names=self.search_tool_names,
            analyst_tool_names=self.analyst_tool_names,
        )
        logger.info(f"Reloaded {len(self.tools)} tools from BlendX Hub")


# Convenience functions for easy usage
def create_search_service_tools(tool_names: List[str] = None) -> List[BaseTool]:
    """
    Convenience function to create SearchService tools from BlendX Hub.

    Args:
        tool_names: Optional list of specific tool names to create

    Returns:
        List of SearchService tool instances
    """
    return SnowflakeToolFactory.create_search_services(tool_names)


def create_data_analyst_tools(tool_names: List[str] = None) -> List[BaseTool]:
    """
    Convenience function to create Data Analyst tools from BlendX Hub.

    Args:
        tool_names: Optional list of specific tool names to create

    Returns:
        List of Data Analyst tool instances
    """
    return SnowflakeToolFactory.create_data_analysts(tool_names)


def create_all_snowflake_tools(
    search_tool_names: List[str] = None,
    analyst_tool_names: List[str] = None,
) -> List[BaseTool]:
    """
    Convenience function to create all Snowflake tools from BlendX Hub.

    Args:
        search_tool_names: Optional list of SearchService tool names to create
        analyst_tool_names: Optional list of Data Analyst tool names to create

    Returns:
        List of all instantiated tool objects
    """
    return SnowflakeToolFactory.create_all_tools(search_tool_names, analyst_tool_names)


def get_snowflake_tools_manager(
    search_tool_names: List[str] = None,
    analyst_tool_names: List[str] = None,
) -> SnowflakeToolsManager:
    """
    Convenience function to get a SnowflakeToolsManager instance.

    Args:
        search_tool_names: Optional list of SearchService tool names to create
        analyst_tool_names: Optional list of Data Analyst tool names to create

    Returns:
        SnowflakeToolsManager instance
    """
    return SnowflakeToolsManager(search_tool_names, analyst_tool_names)
