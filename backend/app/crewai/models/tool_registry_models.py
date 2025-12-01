"""
Tool Registry Models

This module contains Pydantic models for validating tool registry configurations,
including tool implementations, factories, and registry settings.
"""

import os
from typing import Any, Dict, List, Optional, Set, Union

import yaml
from pydantic import BaseModel, Field, field_validator


class CustomToolImplementationConfig(BaseModel):
    """Configuration for tool implementation"""

    implementation: str = Field(..., description="Tool implementation class path")
    config: Optional[Dict[str, Any]] = Field(
        None, description="Tool-specific configuration"
    )


class CrewAIToolImplementationConfig(BaseModel):
    """Configuration for crewai_tool implementation"""

    implementation: Optional[str] = Field(
        None, description="Tool implementation class path (optional for crewai_tools)"
    )
    params: Optional[Dict[str, Any]] = Field(
        None, description="Tool-specific parameters"
    )


class SnowflakeToolFactoryConfig(BaseModel):
    """Configuration for Snowflake tool factory"""

    implementation: str = Field(
        ..., description="Snowflake tool factory implementation"
    )
    tool_type: str = Field(
        ..., description="Type of Snowflake tool (SearchServices, DataAnalysts, etc.)"
    )
    config_path: str = Field(..., description="Path to the tool configuration file")
    tool_names: List[str] = Field(
        ..., description="List of specific tool names to create"
    )


class MCPToolFactoryConfig(BaseModel):
    """Configuration for MCP tool factory"""

    config_path: str = Field(..., description="Path to the MCP configuration file")
    server_names: List[str] = Field(..., description="List of MCP server names")


class ToolsRegistryConfig(BaseModel):
    """Configuration for the tools registry"""

    tools: Dict[
        str,
        Union[
            CustomToolImplementationConfig,
            CrewAIToolImplementationConfig,
            SnowflakeToolFactoryConfig,
            MCPToolFactoryConfig,
        ],
    ] = Field(default_factory=dict, description="Tool configurations")


class ToolsRegistry:
    """Singleton class to cache and manage tools registry with Pydantic validation"""

    _instance = None
    _registry_config = None
    _available_tools = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ToolsRegistry, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._registry_config is None:
            self._load_registry()

    def _load_registry(self):
        """Load and validate the tools registry from YAML file"""
        registry_path = "app/crewai/tools/tools_registry.yaml"
        if not os.path.exists(registry_path):
            self._registry_config = ToolsRegistryConfig()
            self._available_tools = set()
            return

        try:
            with open(registry_path, "r", encoding="utf-8") as f:
                yaml_data = yaml.safe_load(f)

            # Validate the YAML data against our Pydantic model
            self._registry_config = ToolsRegistryConfig(**yaml_data)
            self._build_available_tools()
        except Exception as e:
            # If validation fails, create empty registry
            print(f"Warning: Failed to load tools registry: {e}")
            self._registry_config = ToolsRegistryConfig()
            self._available_tools = set()

    def _build_available_tools(self):
        """Build the set of available tools from the validated registry"""
        self._available_tools = set()

        for tool_name, tool_config in self._registry_config.tools.items():
            if isinstance(tool_config, CustomToolImplementationConfig):
                # Custom tool
                self._available_tools.add(tool_name)
            elif isinstance(tool_config, SnowflakeToolFactoryConfig):
                # Snowflake tool factory - add the tool names
                self._available_tools.update(tool_config.tool_names)
            elif isinstance(tool_config, MCPToolFactoryConfig):
                # MCP tool factory - add the server names
                self._available_tools.update(tool_config.server_names)

    @property
    def registry_config(self) -> ToolsRegistryConfig:
        """Get the validated registry configuration"""
        return self._registry_config

    @property
    def available_tools(self) -> Set[str]:
        """Get all available tool names"""
        return self._available_tools

    def get_snowflake_search_tools(self) -> List[str]:
        """Get available SnowflakeSearchService tools"""
        snowflake_config = self._registry_config.tools.get("SnowflakeSearchService")
        if isinstance(snowflake_config, SnowflakeToolFactoryConfig):
            return snowflake_config.tool_names
        return []

    def get_snowflake_analyst_tools(self) -> List[str]:
        """Get available SnowflakeDataAnalyst tools"""
        snowflake_config = self._registry_config.tools.get("SnowflakeDataAnalyst")
        if isinstance(snowflake_config, SnowflakeToolFactoryConfig):
            return snowflake_config.tool_names
        return []

    def get_mcp_servers(self) -> List[str]:
        """Get available MCP server names"""
        mcp_config = self._registry_config.tools.get("McpFactory")
        if isinstance(mcp_config, MCPToolFactoryConfig):
            return mcp_config.server_names
        return []
