# CrewAI Configuration Template Guide

This guide explains how to use the `config_template.yaml` file to configure CrewAI workflows with different types of tools and agents.

## Configuration Structure

The `config_template.yaml` file contains three main sections:
- `crews`: Defines crew configurations and settings
- `agents`: Defines agent roles, goals, and tools
- `tasks`: Defines tasks and their execution parameters

## Crew Configuration

### Basic Crew Settings
```yaml
crews:
  - name: "Investment Crew"           # Crew name
    process: "sequential"             # "sequential" or "hierarchical"
    verbose: true                     # Show detailed execution logs
    memory: false                     # Enable memory for agents
    agents: ["Agent1", "Agent2"]     # List of agent roles
    tasks: ["Task1", "Task2"]        # List of task names
```

### Hierarchical Crew Settings
```yaml
crews:
  - name: "Hierarchical Crew"
    process: "hierarchical"           # Requires manager agent
    verbose: true
    memory: false
    manager: "Manager Agent"          # Manager agent role (required for hierarchical)
    agents: ["Manager Agent", "Specialist Agent"]
    tasks: ["Task1", "Task2"]
```

## Agent Configuration

### Basic Agent Setup
```yaml
agents:
  - role: "Agent Name"               # Agent's role/title
    goal: "Agent's primary goal"     # What the agent should accomplish
    backstory: "Agent's background"  # Agent's expertise and experience
    tools: []                        # List of tools (see Tool Types below)
    verbose: true                     # Enable verbose logging
    allow_delegation: false          # Allow task delegation
    memory: false                     # Enable memory for this agent
    llm:                             # Optional LLM configuration
      provider: "openai"             # "openai" or "snowflake"
      model: "gpt-4-turbo-preview"  # Model name
      temperature: 0.7               # Generation temperature (0.0-2.0)
```

### LLM Configuration
```yaml
llm:
  provider: "openai"                 # Required: "openai" or "snowflake"
  model: "gpt-4-turbo-preview"      # Required: Model name
  temperature: 0.7                   # Optional: 0.0-2.0, default 0.7
```

## Task Configuration

### Basic Task Setup
```yaml
tasks:
  - name: "Task Name"                # Task identifier
    description: "Task description"  # What the task should do
    agent: "Agent Name"              # Which agent executes this task
    expected_output: "Output description"  # Expected result
    tools: []                        # Tools for this task (see Tool Types)
    context: []                      # Previous task outputs to use
    output_file: null                # File to save output (optional)
```

### Task with Context
```yaml
tasks:
  - name: "Final Report Task"
    description: "Create final report using previous analyses"
    agent: "Report Synthesizer"
    expected_output: "Comprehensive report"
    tools: []
    context: ["Analysis Task", "Research Task"]  # Use outputs from these tasks as content
    output_file: "final_report.txt"
```

## Tool Types

### 1. Custom Tools
Simple tool names for basic functionality:
```yaml
tools:
  - name: "GetStockInfo"
  - name: "GetHistoricalData"
  - name: "GetNews"
```

### 2. Snowflake Service Tools
Tools that connect to Snowflake data warehouse with specific instances:
```yaml
tools:
  - "SnowflakeSearchService": [default_search, search_service_2]
  - "SnowflakeDataAnalyst": [default_analyst]
```

### 3. MCP (Model Context Protocol) Tools
Tools that connect to external MCP servers:
```yaml
tools:
  # Use all tools from MCP server
  - mcp: "YFinance"

  # Use specific tools from MCP server
  - mcp: "YFinance"
    tool_names: ["get_stock_info", "get_historical_data"]
```

### 4. Mixed Tool Types
You can combine different tool types in the same agent/task:
```yaml
tools:
  - name: "GetStockInfo"                    # Custom tool
  - "SnowflakeSearchService": [default_search]  # Snowflake tool
  - mcp: "YFinance"                    # MCP tool
    tool_names: ["get_news"]
```

## Configuration Examples

### Investment Analysis Crew
```yaml
crews:
  - name: "Investment Analysis Crew"
    process: "sequential"
    verbose: true
    memory: false
    agents: ["Financial Analyst", "News Researcher", "Report Writer"]
    tasks: ["Financial Analysis", "News Research", "Report Synthesis"]

agents:
  - role: "Financial Analyst"
    goal: "Analyze financial metrics and market performance"
    backstory: "Senior financial analyst with expertise in fundamental analysis"
    tools:
      - name: "GetStockInfo"
      - name: "GetHistoricalData"
      - "SnowflakeSearchService": [default_search]
    verbose: true
    allow_delegation: false
    llm:
      provider: "openai"
      model: "gpt-4-turbo-preview"
      temperature: 0.7

tasks:
  - name: "Financial Analysis"
    description: "Analyze company financials and market performance"
    agent: "Financial Analyst"
    expected_output: "Detailed financial analysis report"
    tools:
      - name: "GetStockInfo"
      - "SnowflakeSearchService": [default_search]
    context: []
    output_file: null
```

## Environment Variables

Required environment variables for different tool types:
- `SERPER_API_KEY`: For web search tools
- `SNOWFLAKE_*`: For Snowflake connection (if using Snowflake tools)

## Validation

The configuration is validated to ensure:
- All crews reference valid agent roles and task names
- All tasks reference valid agent roles
- All context tasks exist
- Tool configurations are properly formatted
- Required sections are present

## Best Practices

1. **Agent Design**: Give agents clear, specific goals and backstories
2. **Task Sequencing**: Use context to pass information between tasks
3. **Tool Selection**: Choose appropriate tools for each agent's role
4. **LLM Configuration**: Use different models/temperatures for different agent types
5. **Memory Management**: Enable memory for agents that need to remember context
6. **Delegation**: Use hierarchical process for complex workflows requiring coordination