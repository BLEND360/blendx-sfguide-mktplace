"""
Data Analyst Tool

Base class for Snowflake Cortex Analyst tools. Instances are created via the factory from BlendX Hub.
"""

import asyncio
import logging
from typing import Any, Dict, Optional, Union

from crewai.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr

from app.config.settings import get_settings
from app.services.snowflake.data_analyst_service import get_data_analyst_service

logger = logging.getLogger(__name__)


class SnowflakeToolSetupException(Exception):
    pass


class AnalystToolInput(BaseModel):
    """Input schema for AnalystTool"""

    query: Union[str, dict] = Field(
        description="Natural language query for data analysis. Can be a string query or a dictionary with campaign parameters. Ask questions about marketing campaign performance, customer segments, ROI, conversion rates, etc.",
        examples=[
            "What are the top 5 campaign types by conversion rate?",
            "Which customer segments have the highest engagement scores?",
            "What is the average ROI by campaign type?",
            "Which cities perform best for marketing campaigns?",
            "What are the optimal campaign durations for maximum ROI?",
            {
                "campaign_type": "social_media",
                "metrics": ["conversion_rates", "roi_analysis"],
            },
        ],
    )


class AnalystTool(BaseTool):
    """Base tool for analyzing data using Snowflake Cortex Analyst.

    Note: This is a base class. Instances should be created via SnowflakeToolFactory
    which configures them from BlendX Hub.

    Supported connection parameters (from settings):
        - database
        - schema
        - warehouse
        - role
    """

    name: str = "AnalystTool"
    description: str = ""
    args_schema: type[BaseModel] = AnalystToolInput

    # Use PrivateAttr for internal attributes that shouldn't be part of the schema
    _settings = PrivateAttr()
    _data_analyst_service = PrivateAttr()
    _config = PrivateAttr()

    def __init__(
        self,
        timeout=60,
        result_as_answer: bool = False,
    ):
        """
        Initialize the tool with services.

        Args:
            timeout: Tool timeout in seconds
            result_as_answer: If True, forces tool output as final result without agent modification
        """
        super().__init__(timeout=timeout, result_as_answer=result_as_answer)
        self._data_analyst_service = get_data_analyst_service()
        self._settings = get_settings()
        self._config = {}

    def _get_analyst_config(self) -> Dict[str, Any]:
        """
        Get analyst configuration from BlendX Hub settings.

        Returns:
            Dictionary containing analyst configuration
        """
        analyst_config = self._config.get("analyst", {})

        # Check if this is a BlendX Hub service (has hub_metadata)
        is_blendx_hub_service = "hub_metadata" in self._config

        if is_blendx_hub_service:
            # For BlendX Hub services, use BlendX Hub settings as defaults
            logger.info("Using BlendX Hub data analyst configuration")
            config = {
                "max_results": analyst_config.get("max_results", 10),
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
                "filter_mapping": analyst_config.get("filter_mapping", {}),
            }
        else:
            # Fallback to default settings
            logger.info("Using default Snowflake data analyst configuration")
            config = {
                "max_results": 10,
                "database": self._settings.snowflake_database,
                "schema": self._settings.snowflake_schema,
                "warehouse": self._settings.snowflake_warehouse,
                "role": self._settings.snowflake_role,
                "filter_mapping": {},
            }

        return config

    def _build_semantic_model_path(
        self, analyst_config: Dict[str, Any]
    ) -> Optional[str]:
        """
        Build semantic model path from hub_metadata.

        Args:
            analyst_config: Analyst configuration

        Returns:
            Complete semantic model path or None if not found
        """
        # Get stage_path from hub_metadata
        hub_metadata = self._config.get("hub_metadata", {})
        stage_path = hub_metadata.get("stage_path")
        if stage_path:
            logger.info(f"✅ Using stage_path from hub_metadata: {stage_path}")
            return stage_path

        logger.warning("No stage_path found in hub_metadata")
        return None

    def _apply_filters(
        self, query: str, filters: Dict[str, Any], analyst_config: Dict[str, Any]
    ) -> str:
        """
        Apply filters to the query based on the filter mapping configuration.

        Args:
            query: Original query string
            filters: Dictionary of filter key-value pairs
            analyst_config: Analyst configuration containing filter mapping

        Returns:
            Enhanced query string with applied filters
        """
        enhanced_query = query
        filter_mapping = analyst_config.get("filter_mapping", {})

        for filter_key, filter_value in filters.items():
            if filter_value and filter_key in filter_mapping:
                field_name = filter_mapping[filter_key]
                enhanced_query += f" {field_name}:{filter_value}"
            elif filter_value:
                # If no mapping exists, use the filter key directly
                enhanced_query += f" {filter_key}:{filter_value}"

        return enhanced_query

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
        if "campaign_type" in query_dict and query_dict["campaign_type"] != "all":
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
        if "geographic_locations" in query_dict and query_dict["geographic_locations"]:
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

    def _run(
        self,
        query: Union[str, dict],
        semantic_model_path: Optional[str] = None,
        max_results: Optional[int] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Analyze data using Snowflake Cortex Analyst.

        Args:
            query: Natural language query for analysis (string) or dictionary with campaign parameters
            semantic_model_path: Optional path to semantic model (uses config default if not provided)
            max_results: Maximum number of results to return (uses config default if not provided)
            **kwargs: Additional filter parameters

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

            # Get analyst configuration
            analyst_config = self._get_analyst_config()

            # Get semantic model path from hub_metadata
            final_semantic_model_path = (
                semantic_model_path or self._build_semantic_model_path(analyst_config)
            )
            final_max_results = (
                max_results
                if max_results is not None
                else analyst_config["max_results"]
            )

            if not final_semantic_model_path:
                return {
                    "query": query,
                    "original_query": original_query,
                    "error": "Semantic model path not found. Please configure via BlendX Hub.",
                }

            # Prepare filters dictionary
            filters = {k: v for k, v in kwargs.items() if v is not None}

            # Apply filters to query
            enhanced_query = self._apply_filters(query, filters, analyst_config)

            # Run async function in sync context for CrewAI compatibility
            loop = asyncio.get_event_loop()

            if self._data_analyst_service:
                # Prepare connection parameters for dynamic connection
                connection_params = {
                    "database": analyst_config["database"],
                    "schema": analyst_config["schema"],
                    "warehouse": analyst_config["warehouse"],
                    "role": analyst_config["role"],
                }

                # Remove None values from connection params
                connection_params = {
                    k: v for k, v in connection_params.items() if v is not None
                }

                logger.info(f"Using connection parameters: {connection_params}")
                logger.info(f"Using semantic model path: {final_semantic_model_path}")

                # Ask the question using the service with dynamic connection
                result = loop.run_until_complete(
                    self._data_analyst_service.ask_question(
                        query=enhanced_query,
                        semantic_model_path=final_semantic_model_path,
                        connection_params=connection_params,
                    )
                )

                # Extract SQL query and data from the result
                sql_query = (
                    result.get("sql_query") if isinstance(result, dict) else None
                )
                data = result.get("data") if isinstance(result, dict) else result

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
            logger.error(f"Error analyzing data: {str(e)}")
            return {
                "query": query if isinstance(query, str) else str(query),
                "original_query": (
                    original_query if "original_query" in locals() else query
                ),
                "error": f"Failed to analyze data: {str(e)}",
            }

    def validate_connection(self):
        """
        Validate the Snowflake connection for this tool. Raise if not properly set up.
        """
        logger.info(f"🔍 Starting validation for AnalystTool: '{self.name}'")

        config = self._get_analyst_config()
        connection_params = {
            "database": config["database"],
            "schema": config["schema"],
            "warehouse": config["warehouse"],
            "role": config["role"],
        }

        logger.info(
            f"📊 Connection parameters for '{self.name}': database={connection_params['database']}, schema={connection_params['schema']}, warehouse={connection_params['warehouse']}, role={connection_params['role']}"
        )

        logger.info(f"🔌 Testing basic Snowflake connectivity for '{self.name}'...")
        if not self._data_analyst_service.test_connection(connection_params):
            logger.error(f"❌ Snowflake connection failed for tool '{self.name}'")
            raise SnowflakeToolSetupException(
                f"Snowflake AnalystTool '{self.name}' is not properly set up. Check credentials and environment variables."
            )

        logger.info(f"✅ Basic Snowflake connectivity validated for '{self.name}'")
        logger.info(
            f"🎉 Validation completed successfully for AnalystTool: '{self.name}'"
        )

    def get_current_config(self) -> Dict[str, Any]:
        """
        Get the current effective configuration (useful for debugging).

        Returns:
            Dictionary containing the current configuration
        """
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
                "blendx_hub_database": self._settings.blendx_hub_database,
                "blendx_hub_schema": self._settings.blendx_hub_schema,
                "blendx_hub_warehouse": self._settings.blendx_hub_warehouse,
            },
        }
