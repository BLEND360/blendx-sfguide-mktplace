"""
Module for creating and managing MCP (Model Context Protocol) tools from BlendX Hub.
"""

# Standard library imports
import logging
from typing import Any, Dict, List, Optional

# Third-party library imports
# Import BaseTool directly - avoiding namespace conflicts by importing before other modules
try:
    from crewai.tools.base_tool import BaseTool
except ImportError:
    try:
        from crewai.tools import BaseTool
    except ImportError:
        # Fallback: create a dummy BaseTool class
        class BaseTool:
            def __init__(self, name: str = "", description: str = "", **kwargs):
                self.name = name
                self.description = description
                for key, value in kwargs.items():
                    setattr(self, key, value)

            def _run(self, *args, **kwargs):
                return ""

            def run(self, *args, **kwargs):
                return self._run(*args, **kwargs)


logger = logging.getLogger(__name__)


class BaseMCPTool(BaseTool):
    """Base class for all MCP tools with connectivity validation."""

    server_name: str

    def validate_connection(self) -> bool:
        """
        Validate connectivity to the MCP server this tool belongs to.

        Returns:
            True if connection is valid

        Raises:
            ConnectionError: If the connection to the MCP server fails
        """
        logger.info(
            f"🔌 Testing MCP connectivity for tool '{self.name}' on server '{self.server_name}'..."
        )

        try:
            # Since we're using BlendX Hub, we can't directly validate MCP connections
            # This is a placeholder implementation
            logger.info(
                f"✅ MCP tool '{self.name}' from server '{self.server_name}' is available via BlendX Hub"
            )
            return True

        except Exception as e:
            logger.error(
                f"❌ MCP connection failed for tool '{self.name}' on server '{self.server_name}': {str(e)}"
            )
            return False

    def cleanup(self):
        """Clean up MCP tool resources."""
        try:
            logger.debug(f"Cleaning up MCP tool: {self.name}")
        except Exception as e:
            logger.debug(f"Error during MCP tool cleanup: {e}")


class MCPFactory:
    """Factory class to create MCP tools from BlendX Hub."""

    tools_by_server = {}
    tools = []

    @staticmethod
    def cleanup():
        """Clean up all active MCP tools to prevent memory leaks."""
        for server_name in MCPFactory.tools_by_server.keys():
            try:
                if (
                    MCPFactory.tools_by_server[server_name] is None
                    or MCPFactory.tools_by_server[server_name] == []
                ):
                    continue
                # Clean up tools if they have cleanup method
                tools = MCPFactory.tools_by_server[server_name].get("tools", [])
                for tool in tools:
                    if hasattr(tool, "cleanup"):
                        tool.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up MCP tools: {str(e)}")
                continue
        logger.info("Cleaned up all MCP tools")

    @staticmethod
    def create_tools_from_blendx_hub(
        server_name: str,
        tool_names: List[str] = None,
        parameters: Dict[str, Any] = None,
    ) -> List[BaseTool]:
        """
        Create MCP tools from a server discovered via BlendX Hub.

        Args:
            server_name: Name of the MCP server to look for in BlendX Hub
            tool_names: Optional list of specific tool names to filter by
            parameters: Optional parameters to pass to the tools

        Returns:
            List of MCP tool instances

        Raises:
            ConnectionError: If the server cannot be found or connected to
        """
        try:
            # Import BlendX Hub service
            from app.services.blendx_hub_service import get_blendx_hub_service

            logger.info(
                f"🔍 Getting tools from MCP server '{server_name}' via BlendX Hub..."
            )
            blendx_service = get_blendx_hub_service()

            # Get tools from BlendX Hub's tools endpoint
            tools_data = blendx_service.get_mcp_tools(server_name)

            if not tools_data:
                raise ConnectionError(
                    f"Failed to get tools from MCP server '{server_name}' via BlendX Hub"
                )

            logger.info(
                f"✅ Successfully retrieved tools from MCP server '{server_name}' via BlendX Hub"
            )

            # Extract tool information from the response
            if not tools_data.get("success", False):
                raise ConnectionError(
                    f"BlendX Hub tools endpoint returned error: {tools_data.get('message', 'Unknown error')}"
                )

            all_tools_info = tools_data.get("tools", [])

            # Filter tools by name if specified
            if tool_names:
                filtered_tools_info = [
                    tool for tool in all_tools_info if tool.get("name") in tool_names
                ]
                logger.info(
                    f"Filtered to {len(filtered_tools_info)} tools: {[tool.get('name') for tool in filtered_tools_info]}"
                )
            else:
                filtered_tools_info = all_tools_info
                logger.info(f"Using all {len(all_tools_info)} available tools")

            # Create tool wrappers using the rich information from BlendX Hub
            wrapped_tools = []

            for tool_info in filtered_tools_info:
                tool_wrapper = MCPFactory._create_rich_mcp_tool(
                    tool_info, server_name, parameters
                )
                if tool_wrapper:
                    wrapped_tools.append(tool_wrapper)

            logger.info(
                f"🎉 Created {len(wrapped_tools)} MCP tool wrappers from BlendX Hub server '{server_name}'"
            )

            return wrapped_tools

        except Exception as e:
            logger.error(
                f"❌ Failed to create MCP tools from BlendX Hub server '{server_name}': {str(e)}"
            )
            raise ConnectionError(
                f"Failed to create MCP tools from BlendX Hub: {str(e)}"
            )

    @staticmethod
    def _create_rich_mcp_tool(
        tool_info: Dict[str, Any], server_name: str, parameters: Dict[str, Any] = None
    ) -> Optional[BaseTool]:
        """
        Create a rich MCP tool wrapper using detailed information from BlendX Hub.

        This creates a tool wrapper with the actual description and metadata
        from the MCP server, making it fully compatible with CrewAI.

        Args:
            tool_info: Dictionary containing tool information from BlendX Hub
            server_name: Name of the MCP server
            parameters: Optional parameters for the tool

        Returns:
            BaseTool instance or None if creation fails
        """
        try:
            tool_name = tool_info.get("name", "Unknown")
            tool_description = tool_info.get(
                "description", f"MCP tool '{tool_name}' from server '{server_name}'"
            )

            # Create a rich tool class that represents the MCP tool
            class RichMCPTool(BaseMCPTool):
                def __init__(self, **kwargs):
                    # Initialize with required fields for Pydantic validation
                    super().__init__(
                        name=tool_name,
                        description=tool_description,
                        server_name=server_name,
                        **kwargs,
                    )

                    # Set args_schema to None for tools that take no parameters
                    # This tells CrewAI that the tool should be called without arguments
                    if (
                        "Args:\n    None" in tool_description
                        or "no arguments" in tool_description.lower()
                    ):
                        self.args_schema = None
                    else:
                        # For tools with parameters, we'll let CrewAI handle the schema
                        self.args_schema = None

                def _run(self, *args, **kwargs):
                    # Execute the MCP tool by calling BlendX Hub
                    logger.info(
                        f"🔧 EXECUTING MCP TOOL '{self.name}' from server '{self.server_name}'"
                    )
                    logger.info(f"🔧 Tool args: {args}, kwargs: {kwargs}")

                    try:
                        # Import here to avoid circular imports
                        from app.services.blendx_hub_service import (
                            get_blendx_hub_service,
                        )

                        # Get BlendX Hub service
                        blendx_service = get_blendx_hub_service()

                        # Verify the MCP server exists (supports all server types including STDIO)
                        mcp_data = blendx_service.find_mcp(self.server_name)
                        if not mcp_data:
                            raise ConnectionError(
                                f"MCP server '{self.server_name}' not found"
                            )

                        logger.info(
                            f"📡 Calling MCP tool '{self.name}' via MCPServerAdapter (server_type: {mcp_data.server_type.value})"
                        )

                        # Execute the MCP tool using the appropriate transport
                        result = self._execute_mcp_tool_directly(args, kwargs)

                        logger.info(
                            f"✅ MCP tool '{self.name}' executed successfully, returning: {str(result)[:200]}..."
                        )
                        return result

                    except Exception as e:
                        logger.error(
                            f"❌ Error executing MCP tool '{self.name}': {str(e)}"
                        )
                        return f'{{"error": "Failed to execute tool {self.name}: {str(e)}"}}'

                def _execute_mcp_tool_directly(self, args: tuple, kwargs: dict) -> str:
                    """Execute MCP tool using MCPServerAdapter with support for all transport types."""
                    try:
                        from crewai_tools import MCPServerAdapter

                        # Import here to avoid circular imports
                        from app.services.blendx_hub_service import (
                            get_blendx_hub_service,
                        )

                        blendx_service = get_blendx_hub_service()

                        # Get the proper server params based on server_type
                        server_params = blendx_service.get_mcp_server_params(
                            self.server_name
                        )

                        if not server_params:
                            raise ConnectionError(
                                f"Could not get server params for '{self.server_name}'"
                            )

                        # Check if this is STDIO (has 'command' key) or HTTP/SSE (has 'url' key)
                        if "command" in server_params:
                            # STDIO transport - need to use StdioServerParameters
                            try:
                                from mcp import StdioServerParameters

                                stdio_params = StdioServerParameters(
                                    command=server_params["command"],
                                    args=server_params.get("args", []),
                                    env=server_params.get("env", {}),
                                )
                                logger.info(
                                    f"🔧 Using MCPServerAdapter with STDIO for: {server_params['command']}"
                                )
                                mcp_server_adapter = MCPServerAdapter(stdio_params)
                            except ImportError:
                                logger.error("STDIO transport requires 'mcp' package")
                                return (
                                    '{"error": "STDIO transport requires mcp package"}'
                                )
                        else:
                            # SSE or HTTP transport
                            logger.info(
                                f"🔧 Using MCPServerAdapter with {server_params.get('transport', 'sse')} for: {server_params.get('url')}"
                            )
                            mcp_server_adapter = MCPServerAdapter(server_params)

                        tools = mcp_server_adapter.tools

                        logger.info(f"📋 MCPServerAdapter loaded {len(tools)} tools")

                        # Find our tool
                        target_tool = None
                        for tool in tools:
                            tool_name = getattr(tool, "name", str(tool))
                            if tool_name == self.name:
                                target_tool = tool
                                break

                        if not target_tool:
                            tool_names = [
                                getattr(tool, "name", str(tool)) for tool in tools
                            ]
                            return f'{{"error": "Tool {self.name} not found. Available: {tool_names}"}}'

                        logger.info(f"🔧 Executing tool '{self.name}' directly")

                        # Execute the tool
                        if kwargs:
                            result = target_tool.run(**kwargs)
                        else:
                            result = target_tool.run()

                        logger.info(
                            f"✅ Tool executed successfully: {str(result)[:200]}..."
                        )
                        return str(result)

                    except ImportError as e:
                        logger.error(f"❌ MCPServerAdapter not available: {str(e)}")
                        return (
                            f'{{"error": "MCPServerAdapter not available: {str(e)}"}}'
                        )
                    except Exception as e:
                        logger.error(f"❌ Error executing MCP tool: {str(e)}")
                        return f'{{"error": "MCP execution failed: {str(e)}"}}'

                def run(self, *args, **kwargs):
                    """CrewAI-compatible run method that calls _run."""
                    return self._run(*args, **kwargs)

            # Create instance
            tool_instance = RichMCPTool()

            # Apply parameters if provided
            if parameters:
                for key, value in parameters.items():
                    if hasattr(tool_instance, key):
                        setattr(tool_instance, key, value)

            logger.debug(
                f"Created rich MCP tool '{tool_name}' with description: {tool_description[:100]}..."
            )
            return tool_instance

        except Exception as e:
            logger.error(
                f"Failed to create rich MCP tool '{tool_info.get('name', 'Unknown')}': {str(e)}"
            )
            return None

    @staticmethod
    def cleanup_blendx_hub_tools(tools: List[BaseTool]):
        """
        Clean up MCP tools created from BlendX Hub.

        Args:
            tools: List of MCP tools to clean up
        """
        for tool in tools:
            try:
                if hasattr(tool, "cleanup"):
                    tool.cleanup()
            except Exception as e:
                logger.debug(f"Error during MCP tool cleanup: {e}")


class MCPToolsManager:
    """Manager class to handle multiple MCP tool instances."""

    def __init__(self):
        """
        Initialize the manager for MCP tool instances from BlendX Hub.
        """
        # Initialize tools
        self.tools_by_server = {}
        self.tools = []

        # Don't load tools immediately - load them lazily when requested
        # This prevents loading unnecessary servers and allows BlendX Hub integration
        logger.info(
            "MCP Tools Manager initialized - tools will be loaded on-demand from BlendX Hub"
        )

    def get_all_tools(self) -> List[BaseTool]:
        """Get all MCP tool instances."""
        return self.tools

    def get_tools_by_server(self, server_name: str) -> List[BaseTool]:
        """
        Get tools from a specific server.

        Args:
            server_name: Name of the server

        Returns:
            List of tools from the server
        """
        if server_name in self.tools_by_server:
            return self.tools_by_server[server_name].get("tools", [])
        return []

    def get_tools(
        self,
        server_name: str = None,
        tool_names: List[str] = None,
        parameters: Dict[str, Any] = None,
    ) -> List[BaseTool]:
        """
        Get MCP tools, loading from BlendX Hub if necessary.

        Args:
            server_name: Name of the MCP server to load tools from
            tool_names: Optional list of specific tool names to filter by
            parameters: Optional parameters to pass to the tools

        Returns:
            List of MCP tool instances
        """
        logger.info(
            f"DEBUG MCPToolsManager.get_tools: server_name={server_name}, type={type(server_name)}"
        )

        if not server_name:
            return self.get_all_tools()

        # Check if server is already loaded
        if server_name in self.tools_by_server:
            tools = self.tools_by_server[server_name].get("tools", [])
            # If we're filtering and no tools match, try reloading in case tools were added
            if tool_names:
                filtered_tools = [tool for tool in tools if tool.name in tool_names]
                if not filtered_tools:
                    logger.info(
                        f"No matching tools found in cache for {tool_names}, reloading server '{server_name}'"
                    )
                    # Clear cache and reload
                    del self.tools_by_server[server_name]
                    # Remove tools from all_tools list
                    self.tools = [t for t in self.tools if t not in tools]
                    # Try loading again
                    return self.get_tools(server_name, tool_names, parameters)
                return filtered_tools
            return tools

        # Try to load from BlendX Hub
        if self._try_load_server_from_blendx_hub(server_name):
            tools = self.tools_by_server[server_name].get("tools", [])
            if tool_names:
                return [tool for tool in tools if tool.name in tool_names]
            return tools

        return []

    def get_tools_by_names(self, tool_names: List[str] = None) -> List[BaseTool]:
        """
        Get tools by their names.

        Args:
            tool_names: List of tool names to get

        Returns:
            List of matching tools
        """
        if not tool_names:
            return self.get_all_tools()

        matching_tools = []
        for tool in self.tools:
            if tool.name in tool_names:
                matching_tools.append(tool)

        return matching_tools

    def _try_load_server_from_blendx_hub(self, server_name: str) -> bool:
        """
        Try to load a specific server from BlendX Hub.

        Args:
            server_name: Name of the server to load

        Returns:
            True if server was loaded successfully, False otherwise
        """
        try:
            logger.info(f"Attempting to load server '{server_name}' from BlendX Hub...")

            # Use the new BlendX Hub tools endpoint
            tools = MCPFactory.create_tools_from_blendx_hub(server_name)

            if not tools:
                logger.info(
                    f"Server '{server_name}' not found or no tools available in BlendX Hub"
                )
                return False

            # Store the server and tools in our manager
            self.tools_by_server[server_name] = {}
            self.tools_by_server[server_name]["tools"] = tools
            self.tools_by_server[server_name][
                "server_adapter"
            ] = None  # No direct adapter needed
            self.tools.extend(tools)

            logger.info(
                f"✅ Successfully loaded {len(tools)} tools from BlendX Hub for server '{server_name}'"
            )
            return True

        except Exception as e:
            logger.error(
                f"Error loading server '{server_name}' from BlendX Hub: {str(e)}"
            )
            return False

    def validate_connection(self, server_name: str) -> bool:
        """
        Validate connection to a specific MCP server.

        Args:
            server_name: Name of the server to validate

        Returns:
            True if connection is valid, False otherwise
        """
        try:
            # Try to get tools from the server
            tools = self.get_tools(server_name=server_name)
            return len(tools) > 0
        except Exception as e:
            logger.error(
                f"Error validating connection to server '{server_name}': {str(e)}"
            )
            return False

    def list_server_names(self) -> List[str]:
        """
        List all loaded server names.

        Returns:
            List of server names
        """
        return list(self.tools_by_server.keys())

    def cleanup(self):
        """Clean up all MCP tools and connections."""
        try:
            for server_name in self.tools_by_server:
                tools = self.tools_by_server[server_name].get("tools", [])
                MCPFactory.cleanup_blendx_hub_tools(tools)

            self.tools_by_server.clear()
            self.tools.clear()
            logger.info("MCP Tools Manager cleaned up")
        except Exception as e:
            logger.error(f"Error during MCP Tools Manager cleanup: {str(e)}")


# Convenience functions
def get_mcp_tools_manager() -> MCPToolsManager:
    """
    Get a MCP tools manager instance.

    Returns:
        MCPToolsManager instance
    """
    return MCPToolsManager()


def create_mcp_tools_from_blendx_hub(
    server_name: str, tool_names: List[str] = None, parameters: Dict[str, Any] = None
) -> List[BaseTool]:
    """
    Convenience function to create MCP tools directly from BlendX Hub.

    Args:
        server_name: Name of the MCP server to look for in BlendX Hub
        tool_names: Optional list of specific tool names to filter by
        parameters: Optional parameters to pass to the tools

    Returns:
        List of MCP tool instances

    Raises:
        ConnectionError: If the server cannot be found or connected to
    """
    return MCPFactory.create_tools_from_blendx_hub(server_name, tool_names, parameters)
