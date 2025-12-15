# Snowflake Tools for CrewAI

This guide explains how to use the custom Snowflake tools for CrewAI agents. All tools are configured exclusively through **BlendX Hub**.

## Available Tools

### AnalystTool
Analyze data using Snowflake Cortex Analyst with natural language queries. Tool instances are dynamically created from data analysts registered in BlendX Hub.

### SearchService
Perform vector searches in Snowflake databases using Cortex Search Service. Tool instances are dynamically created from search services registered in BlendX Hub.

## Installation

```bash
uv add crewai crewai-tools
```

## Configuration

All tools are configured through **BlendX Hub** - no local YAML configuration files are needed.

### Environment Variables

Configure these environment variables in your `.env` file:

```bash
# BlendX Hub Connection (required)
BLENDX_HUB_URL=https://your-blendx-hub-url

# BlendX Hub Snowflake Settings (used for Hub-managed tools)
BLENDX_HUB_DATABASE=your_hub_database
BLENDX_HUB_SCHEMA=your_hub_schema
BLENDX_HUB_WAREHOUSE=your_hub_warehouse

# Snowflake Connection (fallback/default values)
SNOWFLAKE_USER=your_user
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_WAREHOUSE=your_warehouse
SNOWFLAKE_DATABASE=your_database
SNOWFLAKE_SCHEMA=your_schema
SNOWFLAKE_ROLE=your_role
```

### BlendX Hub Configuration

Tools are registered and managed through BlendX Hub:

1. **Search Services**: Register Cortex Search Services in BlendX Hub with their service names, descriptions, and metadata
2. **Data Analysts**: Register Cortex Data Analysts in BlendX Hub with their semantic model paths and descriptions

The factory automatically fetches available services from BlendX Hub and creates tool instances.

## Usage

### Factory Pattern (Recommended)

Use the factory to create tool instances from BlendX Hub:

```python
from app.crewai.tools.snowflake_tools.snowflake_tools_factory import (
    create_search_service_tools,
    create_data_analyst_tools,
    create_all_snowflake_tools,
    get_snowflake_tools_manager
)

# Create all available tools from BlendX Hub
all_tools = create_all_snowflake_tools()

# Create specific tool types
search_tools = create_search_service_tools()
analyst_tools = create_data_analyst_tools()

# Create specific tools by name
specific_search_tools = create_search_service_tools(
    tool_names=["my_search_service", "another_search_service"]
)
specific_analyst_tools = create_data_analyst_tools(
    tool_names=["my_data_analyst"]
)
```

### Using the Tools Manager

For advanced control over tool instances:

```python
from app.crewai.tools.snowflake_tools.snowflake_tools_factory import (
    get_snowflake_tools_manager
)

# Create manager with all tools
manager = get_snowflake_tools_manager()

# Or create manager with specific tools only
manager = get_snowflake_tools_manager(
    search_tool_names=["my_search_service"],
    analyst_tool_names=["my_data_analyst"]
)

# Get all tools
all_tools = manager.get_all_tools()
print(f"Total tools loaded: {len(all_tools)}")
print(f"Tool names: {manager.list_tool_names()}")

# Get tools by type
search_tools = manager.get_tools_by_type("SearchService")
analyst_tools = manager.get_tools_by_type("AnalystTool")

# Get specific tool by name
my_search = manager.get_tool_by_name("my_search_service")
my_analyst = manager.get_tool_by_name("my_data_analyst")

# Reload tools if BlendX Hub configuration changes
manager.reload_tools()
```

### CrewAI Agent Integration

```python
from crewai import Agent, Task, Crew
from app.crewai.tools.snowflake_tools.snowflake_tools_factory import (
    create_all_snowflake_tools,
    get_snowflake_tools_manager
)

# Get tools from BlendX Hub
manager = get_snowflake_tools_manager()
tools = manager.get_all_tools()

# Create agent with tools
analyst = Agent(
    role="Business Intelligence Analyst",
    goal="Analyze business data and find insights",
    backstory="Expert at interpreting data and providing actionable insights",
    tools=tools,
    verbose=True
)

# Create task
analysis_task = Task(
    description="""
    Analyze Q4 sales performance:
    1. Search for relevant sales documents and reports
    2. Query the data analyst for sales metrics
    3. Identify trends and top performers
    """,
    expected_output="Comprehensive analysis with key metrics and insights",
    agent=analyst
)

# Execute
crew = Crew(agents=[analyst], tasks=[analysis_task])
result = crew.kickoff()
```

### Department-Specific Agents Example

```python
manager = get_snowflake_tools_manager()

# Financial Department Agent
financial_agent = Agent(
    role="Financial Analyst",
    goal="Analyze financial performance and metrics",
    tools=[
        manager.get_tool_by_name("financial_analyst"),
        manager.get_tool_by_name("sec_search_service")
    ],
    backstory="Expert in financial analysis"
)

# Sales Department Agent
sales_agent = Agent(
    role="Sales Analyst",
    goal="Analyze sales performance and customer trends",
    tools=[
        manager.get_tool_by_name("sales_analyst"),
        manager.get_tool_by_name("customer_search_service")
    ],
    backstory="Expert in sales analysis"
)
```

## Tool Interface

Both tools use a **query-only interface**. All configuration comes from BlendX Hub.

### AnalystTool

```python
# Method signature
def _run(self, query: Union[str, dict]) -> Dict[str, Any]

# Example queries
result = analyst_tool._run("What are the top 5 products by revenue?")
result = analyst_tool._run("Show monthly sales trends for Q4 2024")
```

### SearchService

```python
# Method signature
def _run(self, query: str) -> Dict[str, Any]

# Example queries
result = search_tool._run("Q4 2024 revenue reports")
result = search_tool._run("customer satisfaction surveys")
```

## Return Value Structure

### AnalystTool Response

```python
{
    "query": "original query string",
    "original_query": "original query (before conversion if dict)",
    "enhanced_query": "processed query string",
    "sql_query": "generated SQL query",
    "data": [...],                    # Analysis results
    "total_items": 25,                # Total items found
    "returned_items": 10,             # Items returned (limited by max_results)
    "config_used": {
        "semantic_model_path": "@db.schema.stage/model.yaml",
        "database": "...",
        "schema": "...",
        "warehouse": "...",
        "role": "...",
        "max_results": 10
    }
}
```

### SearchService Response

```python
{
    "query": "original query string",
    "enhanced_query": "processed query string",
    "results": [...],                 # Search results
    "result_count": 5,                # Number of results returned
    "config_used": {
        "service_name": "my_search_service",
        "database": "...",
        "schema": "...",
        "warehouse": "...",
        "role": "...",
        "num_results": 5
    }
}
```

## Debugging

### Check Tool Configuration

```python
# Get current effective configuration
config = tool.get_current_config()
print(f"Tool name: {config['tool_name']}")
print(f"Description: {config['tool_description']}")
print(f"Settings: {config.get('analyst_config', config.get('search_config'))}")
```

### Validate Connection

```python
# Validate Snowflake connection before use
try:
    tool.validate_connection()
    print("Connection validated successfully")
except SnowflakeToolSetupException as e:
    print(f"Connection validation failed: {e}")
```

## Troubleshooting

### Common Issues

1. **BlendX Hub Connection Failed**
   ```
   Error: Failed to fetch search services from BlendX Hub
   ```
   **Solution**: Verify `BLENDX_HUB_URL` is set correctly and the service is accessible

2. **No Tools Created**
   ```
   Warning: No active data analysts found in BlendX Hub
   ```
   **Solution**: Ensure tools are registered and have `ACTIVE` status in BlendX Hub

3. **Semantic Model Path Not Found**
   ```
   Error: Semantic model path not found in BlendX Hub configuration
   ```
   **Solution**: Verify the data analyst in BlendX Hub has a valid `stage_path` configured

4. **Connection Failed**
   ```
   Error: Snowflake service not available
   ```
   **Solution**: Check Snowflake credentials and network connectivity

5. **Tool Not Found**
   ```
   Requested search services not found in BlendX Hub: ['my_tool']
   ```
   **Solution**: Verify the tool name matches exactly what's registered in BlendX Hub

## Architecture

```
BlendX Hub
    │
    ├── Search Services (Cortex Search)
    │   ├── service_name
    │   ├── description
    │   ├── total_documents
    │   └── metadata_columns
    │
    └── Data Analysts (Cortex Analyst)
        ├── data_analyst_name
        ├── description
        ├── stage_path (semantic model)
        └── tables_referenced

        ↓

SnowflakeToolFactory
    │
    ├── create_search_services()
    │   └── Fetches from BlendX Hub API
    │       └── Creates HubSearchService instances
    │
    └── create_data_analysts()
        └── Fetches from BlendX Hub API
            └── Creates HubAnalystTool instances

        ↓

CrewAI Agents
    └── Use tools with simple query interface
```

## API Reference

### Factory Functions

| Function | Description |
|----------|-------------|
| `create_search_service_tools(tool_names=None)` | Create SearchService tools from BlendX Hub |
| `create_data_analyst_tools(tool_names=None)` | Create Data Analyst tools from BlendX Hub |
| `create_all_snowflake_tools(search_tool_names=None, analyst_tool_names=None)` | Create all tools from BlendX Hub |
| `get_snowflake_tools_manager(search_tool_names=None, analyst_tool_names=None)` | Get a SnowflakeToolsManager instance |

### SnowflakeToolsManager Methods

| Method | Description |
|--------|-------------|
| `get_all_tools()` | Get all tool instances |
| `get_tools_by_type(tool_type)` | Get tools filtered by type ('SearchService', 'AnalystTool') |
| `get_tool_by_name(name)` | Get a specific tool by name |
| `list_tool_names()` | Get list of all tool names |
| `reload_tools()` | Reload all tools from BlendX Hub |

### Tool Methods

| Method | Description |
|--------|-------------|
| `_run(query)` | Execute query (main interface) |
| `get_current_config()` | Get current effective configuration |
| `validate_connection()` | Validate Snowflake connection |
