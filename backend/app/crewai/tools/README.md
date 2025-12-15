# CrewAI Tools Configuration Guide

This guide explains how to configure and register tools for use in CrewAI, including custom tools, Snowflake services tools, and MCP tools. All tool configurations are managed in the `tools_registry.yaml` file.

## How the Tool Registry Works

The `tools_registry.yaml` file serves as the central registry that the CrewAI application uses to:
- **Build crews and flows from YAML configurations** - When you define agents and tasks in YAML files, the application looks up tool names in the registry to instantiate the actual tool classes
- **Add tools to agents and tasks** - Tools registered in the registry can be referenced by name in your YAML crew/flow configurations
- **Manage tool dependencies and configurations** - The registry stores implementation classes, configuration parameters, and factory settings for complex tools

This registry-based approach allows you to define crews and flows entirely in YAML without writing Python code for tool instantiation. Simply register your tools in the registry, then reference them by name in your YAML configurations.

---

## Where to Configure Tools

- All tool registrations and configuration are managed in:
  - [`app/crewai/tools/tools_registry.yaml`](tools_registry.yaml)
- Each tool entry specifies its implementation class and any configuration parameters.

---

This YAML file serves as the central registry for all available tools that can be used by CrewAI agents and tasks.

## Example: Registering a Custom Tool

Here's how to register a custom tool in the tools registry:

```yaml
tools:
  MyCustomTool:
    implementation: "app.crewai.tools.my_custom_tool.MyCustomTool"
    config:
      param1: value1
      param2: value2
```
- Reference `MyCustomTool` in your agent or task YAML to use it.

---

## Snowflake Services Tools
CrewAI supports advanced Snowflake tools for RAG search and data analysis (text-to-SQL, etc). These are registered using the `SnowflakeToolFactory` and configured via YAML.

### Step 1: Configure Snowflake Tool Instances
Before registering in `tools_registry.yaml`, you must first configure the Snowflake tool instances in their respective config files:

- **Search Services**: Configure in [`app/crewai/tools/snowflake_tools/search_service_tool/search_service_tool_config.yaml`](snowflake_tools/search_service_tool/search_service_tool_config.yaml)
- **Data Analysts**: Configure in [`app/crewai/tools/snowflake_tools/data_analyst_tool/data_analyst_tool_config.yaml`](snowflake_tools/data_analyst_tool/data_analyst_tool_config.yaml)

These config files define the specific instances (like `default_search`, `default_analyst`) that will be built by the factories.

### Step 2: Register in tools_registry.yaml
```yaml
tools:
  SnowflakeSearchService:
    implementation: "app.crewai.tools.snowflake_tools.snowflake_tools_factory.SnowflakeToolFactory"
    config:
      tool_type: "SearchServices"
      config_path: "app/crewai/tools/snowflake_tools/search_service_tool/search_service_tool_config.yaml"
      tool_names: ["default_search"]

  SnowflakeDataAnalyst:
    implementation: "app.crewai.tools.snowflake_tools.snowflake_tools_factory.SnowflakeToolFactory"
    config:
      tool_type: "DataAnalysts"
      config_path: "app/crewai/tools/snowflake_tools/data_analyst_tool/data_analyst_tool_config.yaml"
      tool_names: ["default_analyst"]
```
- Reference `SnowflakeSearchService` or `SnowflakeDataAnalyst` in your agent/task YAML.
- For advanced configuration, see [`snowflake_tools_factory.py`](snowflake_tools/snowflake_tools_factory.py) and [`README.md`](snowflake_tools/README.md).

---

## MCP Tools (Model Control Protocol)
CrewAI can connect to external MCP servers to use remote tools (e.g., financial data, custom APIs).

### MCP Tools (via BlendX Hub)
MCP tools are now automatically discovered through BlendX Hub. No configuration is needed in `tools_registry.yaml`.
- Reference MCP tools in your agent/task YAML using the MCP server name and (optionally) tool names.
- For advanced configuration, see [`mcp_factory.py`](../mcp/mcp_factory.py) and [`README.md`](../mcp/README.md).

---

## 5️⃣ Referencing Tools in Agents/Tasks

### Agents
In agent configurations, tools are referenced using the `name` field:
```yaml
agents:
  - role: "Investment Advisor"
    tools:
      - name: "GetStockInfo"
      - name: "GetHistoricalData"
      - name: "SerperDev"
```

### Tasks
In task configurations, tools can be referenced in different ways depending on the tool type:

#### Standard Tools
```yaml
tasks:
  - name: "Research Task"
    tools:
      - name: "SerperDev"
      - name: "WebsiteSearch"
```

#### Snowflake Tools (with instances)
```yaml
tasks:
  - name: "Financial Analysis Task"
    tools:
      - "SnowflakeSearchService": [default_search]
      - "SnowflakeDataAnalyst": [default_analyst]
```

#### MCP Tools
```yaml
tasks:
  - name: "Market Analysis Task"
    tools:
      - MCP: "YFinance"  # Access all tools in the MCP server
      - MCP: "YFinance"      # Access specific tools only
        tool_names: ["get_stock_info", "compare_stocks", "calculate_correlation"]
```

---

## More Resources
- [Snowflake Tools Factory README](snowflake_tools/README.md)
- [MCP Factory README](../mcp/README.md)
- [Orchestration YAML Tutorial](../engine/README.md)

---
