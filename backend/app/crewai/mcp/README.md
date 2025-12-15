# MCP Factory and Tools Manager

This module provides a unified factory system for creating and managing MCP (Model Context Protocol) tools from BlendX Hub.

## Overview

The MCP Factory system consists of:

1. **MCPFactory**: Static factory class for creating MCP tools from BlendX Hub
2. **MCPToolsManager**: Manager class for handling multiple MCP tool instances
3. **BlendX Hub Integration**: Automatic discovery of MCP servers and tools via BlendX Hub
4. **Convenience Functions**: Easy-to-use functions for common operations

## Quick Start

### 1. Create MCP Tools from BlendX Hub

```python
from app.crewai.mcp.mcp_factory import create_mcp_tools_from_blendx_hub

# Create tools from a specific MCP server
tools = create_mcp_tools_from_blendx_hub("YFinance")

# Create specific tools
tools = create_mcp_tools_from_blendx_hub("YFinance", tool_names=["get_stock_info", "compare_stocks"])
```

### 2. Use MCPToolsManager

```python
from app.crewai.mcp.mcp_factory import get_mcp_tools_manager

# Create manager
manager = get_mcp_tools_manager()

# Get tools by server (loads from BlendX Hub automatically)
yfinance_tools = manager.get_tools_by_server('YFinance')

# Get specific tools by names
specific_tools = manager.get_tools_by_names(['get_stock_info', 'compare_stocks'])

# List available servers
servers = manager.list_server_names()
```

### 3. Use with CrewAI

```python
from app.crewai.mcp.mcp_factory import get_mcp_tools_manager

# Create manager
manager = get_mcp_tools_manager()

# Get tools for agents (loads from BlendX Hub automatically)
agent_tools = manager.get_tools_by_server('YFinance')

# Create agent with MCP tools
from crewai import Agent
agent = Agent(
    role="Investment Analyst",
    goal="Analyze stocks and provide investment recommendations",
    backstory="Expert financial analyst with access to real-time market data",
    tools=agent_tools
)
```

## Configuration

### BlendX Hub Integration

MCP tools are now automatically discovered through BlendX Hub. No YAML configuration is needed.

The system will:
1. Query BlendX Hub for available MCP servers
2. Get tools from each server via BlendX Hub's `/mcp/tools` endpoint
3. Create tool wrappers for use in CrewAI agents and tasks

## API Reference

### MCPFactory Class

#### Static Methods

- `create_tools_from_blendx_hub(server_name, tool_names=None, parameters=None)`
  - Creates MCP tools from a specific server via BlendX Hub
  - Returns: List of BaseTool instances

- `_create_mock_mcp_tool(tool_name, server_name, parameters=None)`
  - Creates a mock MCP tool wrapper
  - Returns: BaseTool instance or None

### MCPToolsManager Class

#### Constructor

```python
MCPToolsManager()
```

#### Methods

- `get_all_tools()` → List[BaseTool]
  - Get all MCP tool instances

- `get_tools_by_server(server_name: str)` → List[BaseTool]
  - Get tools from a specific server

- `get_tools(server_name=None, tool_names=None, parameters=None)` → List[BaseTool]
  - Get MCP tools, loading from BlendX Hub if necessary

- `get_tools_by_names(tool_names: List[str])` → List[BaseTool]
  - Get tools by their names

- `list_server_names()` → List[str]
  - List all loaded server names

- `validate_connection(server_name: str)` → bool
  - Validate connection to a specific MCP server

- `cleanup()`
  - Clean up all MCP tools and connections

### Convenience Functions

- `get_mcp_tools_manager()` → MCPToolsManager
  - Get a MCP tools manager instance

- `create_mcp_tools_from_blendx_hub(server_name, tool_names=None, parameters=None)` → List[BaseTool]
  - Create MCP tools directly from BlendX Hub

## Usage in YAML Configurations

MCP tools can be referenced in agent and task configurations:

```yaml
agents:
  - role: "Investment Advisor"
    tools:
      - mcp: ["YFinance"]
        tool_names: ["get_stock_info", "compare_stocks"]

tasks:
  - name: "Market Analysis Task"
    tools:
      - mcp: ["YFinance"]
        tool_names: ["get_stock_info", "compare_stocks", "calculate_correlation"]
```

## Error Handling

The system includes comprehensive error handling:

- **Connection Errors**: If BlendX Hub is not accessible
- **Server Not Found**: If the requested MCP server is not available
- **Tool Discovery Errors**: If tools cannot be retrieved from BlendX Hub

All errors are logged with appropriate detail levels for debugging.

## Dependencies

- `crewai.tools.BaseTool`: Base class for all tools
- `app.services.blendx_hub_service`: BlendX Hub integration service
- `httpx`: HTTP client for API calls

## Notes

- MCP tools are created as mock wrappers since we only get tool names from BlendX Hub
- In production, you might want to enhance the mock tools to make actual calls to BlendX Hub
- The system maintains compatibility with existing CrewAI tool interfaces