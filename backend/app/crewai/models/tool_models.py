"""
Tool Models

This module contains Pydantic models for validating tool configurations
used in crew and task definitions.
"""

import logging
from typing import Any, List, Optional, Union

from pydantic import BaseModel, Field, RootModel, model_validator

from app.crewai.models.tool_registry_models import ToolsRegistry

# Global instance
tools_registry = ToolsRegistry()


class CrewAIToolsConfig(BaseModel):
    """Configuration for crewai_tools from the crewai_tools library"""

    crewai_tools: List[str] = Field(..., description="List of crewai_tools to load")

    @model_validator(mode="after")
    def validate_crewai_tools(self):
        """Validate that crewai_tools are valid and exist in the library"""
        try:
            import crewai_tools

            available_tools = dir(crewai_tools)

            for tool_name in self.crewai_tools:
                if not isinstance(tool_name, str) or not tool_name.strip():
                    raise ValueError(f"Invalid crewai_tool name: {tool_name}")

                if tool_name not in available_tools:
                    raise ValueError(
                        f"CrewAI tool '{tool_name}' not found in crewai_tools library. Available tools: {available_tools}"
                    )

        except ImportError:
            # If crewai_tools is not installed, just do basic validation
            for tool_name in self.crewai_tools:
                if not isinstance(tool_name, str) or not tool_name.strip():
                    raise ValueError(f"Invalid crewai_tool name: {tool_name}")

        return self


class CustomToolsConfig(BaseModel):
    """Configuration for custom_tools using the new syntax"""

    custom_tools: List[str] = Field(..., description="List of custom tools to load")

    @model_validator(mode="after")
    def validate_custom_tools_exist(self):
        """Validate that the custom tools exist in the registry"""
        for tool_name in self.custom_tools:
            if tool_name not in tools_registry.available_tools:
                raise ValueError(
                    f"Custom tool '{tool_name}' not found in tools registry"
                )
        return self


class SnowflakeToolConfig(BaseModel):
    SnowflakeSearchService: Optional[List[str]] = None
    SnowflakeDataAnalyst: Optional[List[str]] = None

    @model_validator(mode="after")
    def validate_instance_lists(self):
        values = [self.SnowflakeSearchService, self.SnowflakeDataAnalyst]
        if not any(values):
            raise ValueError(
                "One of SnowflakeSearchService or SnowflakeDataAnalyst must be provided"
            )

        for tool_list in filter(None, values):
            if not isinstance(tool_list, list) or not all(
                isinstance(i, str) for i in tool_list
            ):
                raise ValueError("Tool values must be lists of strings")
        return self

    @model_validator(mode="after")
    def validate_snowflake_tools_exist(self):
        """Validate that Snowflake tools exist in the registry"""
        # Check SnowflakeSearchService tools
        if self.SnowflakeSearchService:
            available_tools = tools_registry.get_snowflake_search_tools()
            for tool_name in self.SnowflakeSearchService:
                if tool_name not in available_tools:
                    raise ValueError(
                        f"SnowflakeSearchService tool '{tool_name}' not found in registry"
                    )

        # Check SnowflakeDataAnalyst tools
        if self.SnowflakeDataAnalyst:
            # For Data Analysts, we don't validate against registry since they come from BlendX Hub
            # The actual validation happens at runtime when the tools are created
            logger = logging.getLogger(__name__)
            logger.info(
                f"Data Analysts from Hub will be validated at runtime: {self.SnowflakeDataAnalyst}"
            )

        return self

    class Config:
        extra = "forbid"


class MCPToolConfig(BaseModel):
    """Configuration for MCP tool"""

    mcp: List[str] = Field(..., description="MCP server names")
    tool_names: Optional[List[str]] = Field(
        None, description="Specific tool names from MCP server"
    )

    @model_validator(mode="after")
    def validate_mcp_servers_exist(self):
        """Validate that MCP servers are available via BlendX Hub"""
        # Since we now use BlendX Hub for MCP discovery, we don't need to validate
        # against a static registry. The actual validation happens at runtime when
        # tools are created through BlendX Hub.

        # Basic validation: ensure server names are not empty
        for server_name in self.mcp:
            if not server_name or not isinstance(server_name, str):
                raise ValueError(f"Invalid MCP server name: '{server_name}'")

        return self

    class Config:
        extra = "forbid"


class SearchServiceToolConfig(BaseModel):
    """Configuration for search service tools from BlendX Hub"""

    search_service: Union[str, List[str]] = Field(
        ..., description="Search service name(s) from BlendX Hub"
    )
    tool_names: Optional[List[str]] = Field(
        None, description="Specific tool names to create for the service"
    )

    @model_validator(mode="after")
    def validate_search_service_exists(self):
        """Validate that search service exists in BlendX Hub"""
        # Since we use BlendX Hub for search service discovery, we don't need to validate
        # against a static registry. The actual validation happens at runtime when
        # tools are created through BlendX Hub.

        # Basic validation: ensure service name is not empty
        if isinstance(self.search_service, str):
            if not self.search_service.strip():
                raise ValueError("Search service name cannot be empty")
        elif isinstance(self.search_service, list):
            for service_name in self.search_service:
                if (
                    not service_name
                    or not isinstance(service_name, str)
                    or not service_name.strip()
                ):
                    raise ValueError(f"Invalid search service name: '{service_name}'")

        return self

    class Config:
        extra = "forbid"


class Tool(RootModel):
    """Unified tool model that can handle all tool formats"""

    # Union of all possible tool types
    root: Union[
        CrewAIToolsConfig,
        CustomToolsConfig,
        SnowflakeToolConfig,
        MCPToolConfig,
        SearchServiceToolConfig,
    ]
