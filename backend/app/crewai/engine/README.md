# YAML Workflow Engine: Configuration-Driven Execution

The BlendX Core YAML Engine allows you to define and execute AI workflows using declarative YAML configuration files—no Python coding required. This engine is the core component that powers BlendX Core's YAML-based workflow execution for both **Crews** (multi-agent collaboration) and **Flows** (stateful processes).

## What is the YAML Engine?

The YAML Engine is BlendX Core's configuration-to-execution system that:
- **Parses** YAML workflow definitions
- **Validates** configurations against schemas
- **Builds** CrewAI objects (agents, tasks, crews, flows)
- **Executes** workflows through the unified orchestration builder
- **Returns** results via the FastAPI endpoints

This enables non-developers to create and run complex AI workflows using simple YAML files.


## About CrewAI

CrewAI is a framework for orchestrating role-playing autonomous AI agents. It enables you to create multi-agent systems where agents can work together to accomplish complex tasks. Crews are groups of agents that collaborate on tasks, while flows provide more complex orchestration with state management and conditional logic.

**Key Concepts:**
- **Agents**: AI entities with specific roles, goals, and tools
- **Tasks**: Specific assignments given to agents
- **Crews**: Groups of agents working together on related tasks
- **Flows**: Complex workflows with state management and conditional execution

For comprehensive documentation on CrewAI concepts, agents, tasks, and advanced features, visit the [official CrewAI documentation](https://docs.crewai.com/).


---

## How the Engine Works in BlendX Core

### Execution Flow

```
User Request (via API)
    ↓
YAML Configuration
    ↓
Engine Parser & Validator
    ↓
CrewAI Object Builder
    ↓
Workflow Executor
    ↓
Result (via API response)
```

### Key Components

1. **YAML Parser**: Reads and validates YAML configurations
2. **Schema Validator**: Ensures configurations match expected format
3. **Object Builder**: Creates CrewAI agents, tasks, crews, and flows
4. **Orchestration Runner**: Executes the workflow
5. **Result Handler**: Formats and returns execution results

### Integration with BlendX Core

The engine integrates with BlendX Core through:
- **FastAPI Endpoints**: `/run-build-crew`, `/run-build-crew-async`, `/run-build-flow`, `/run-build-flow-async`
- **Natural Language Generator**: Generates YAML from user requests
- **Execution Manager**: Tracks async workflow execution
- **Database Logger**: Persists execution history (when enabled)

## What You Can Build

With the YAML Engine, you can:

- **Define Multi-Agent Workflows**: Create crews with specialized agents
- **Build Stateful Processes**: Design flows with conditional logic
- **Integrate External Tools**: Use Snowflake Cortex, MCP servers, custom tools
- **Execute via API**: Trigger workflows programmatically
- **Monitor Execution**: Track progress and retrieve results

### Tool Integration

Expand capabilities by:
- **Custom Tools**: Implement Python tools and register in `tools_registry.yaml`
- **MCP Servers**: Integrate external services via Model Context Protocol
- **Snowflake Tools**: Leverage Cortex Search (RAG) or Data Analyst (text-to-SQL)

All tools are automatically available in YAML configurations—no code changes needed.

---

## Key Files
- `build_orchestration.py` — Unified builder to run and manage both crews and flows from YAML config
- `config/` — Example YAML configurations for both crews and flows

---

## Crew Orchestration with YAML (Using Unified Builder)

### **YAML Structure for Crews**
A minimal crew YAML config might look like:
```yaml
agents:
  - role: "Research Analyst"
    goal: "Research a topic"
    backstory: "Expert in research"
    tools: ["web_search"]
    verbose: true

tasks:
  - name: "Research Topic"
    description: "Research and summarize the topic: ${input}"
    agent: "Research Analyst"
    expected_output: "Summary of findings"
    tools: ["web_search"]

crews:
  - name: "Research Crew"
    agents: ["Research Analyst"]
    tasks: ["Research Topic"]
    verbose: true
    memory: false
```

- **Multiple Crews/Flows:**
  - You can define and run multiple crews or flows in a single YAML config.
  - For crews, use a list under the `crews:` key; for flows, define multiple flow steps or methods.
  - Example (multiple crews):
    ```yaml
    crews:
      - name: "Research Crew"
        agents: ["Research Analyst"]
        tasks: ["Research Topic"]
      - name: "Analysis Crew"
        agents: ["Data Analyst"]
        tasks: ["Analyze Data"]
    ```
  - Both crews will be created and can be run in parallel or sequence depending on your setup.


For more details and examples of all the different configuration options, please reference [`config/config_template.yaml`](config/config_template.yaml).


You can also use the API endpoints provided by the application to run crews and flows. And use the script yaml_transformer.py to convert a YAML configuration files in a directory to a format that can be used by the API.

### **How to Run**
You can run crews via the CLI or FastAPI API endpoints.

#### **Run with CLI**
```bash
python app/crewai/engine/build_orchestration.py path/to/config/directory --type crew
```
- The script will load `agents.yaml`, `tasks.yaml`, and `crews.yaml` from the directory.

#### **Run with FastAPI**
Start the server:
```bash
uvicorn main:app --host 0.0.0.0 --port 3002
```
Then use the API endpoint:
```bash
curl -X POST "http://localhost:3002/run-build-crews" \
     -H "Content-Type: application/json" \
     -d '{"yaml_text": "<your yaml here>", "input": "<your input here>"}'
```
- You can also use `/run-build-crews-async` for async execution.
- See the FastAPI docs for more endpoints and options.

### **Features**
- Supports multiple agents, tasks, and crews
- Handles context and dependencies between tasks
- Integrates with custom and built-in tools
- Supports hierarchical and sequential crew processes
- Can be run via CLI or FastAPI

---

## Flow Orchestration with YAML (Using Unified Builder)

### **YAML Structure for Flows**
A minimal flow YAML config might look like:
```yaml
name: "Research Flow"
flow:
  class_name: "ResearchFlow"
  # Define flow logic and steps here

agents:
  - role: "Research Analyst"
    goal: "Research a topic"
    backstory: "Expert in research"
    tools: ["web_search"]
    verbose: true

tasks:
  - name: "Research Topic"
    description: "Research and summarize the topic: ${input}"
    agent: "Research Analyst"
    expected_output: "Summary of findings"
    tools: ["web_search"]

flow_methods:
  - name: "start_research"
    type: "start"
    action: "run_crew"
    crew: "default_crew"
    output: "Research started"
```

### **How to Run**
You can run flows via the CLI or FastAPI API endpoints.

#### **Run with CLI**
```bash
python app/crewai/engine/build_orchestration.py path/to/config/directory --type flow
```
- The script will load `flow.yaml`, `agents.yaml`, `tasks.yaml`, and `flow_methods.yaml` from the directory.

#### **Run with FastAPI**
Start the server:
```bash
uvicorn main:app --host 0.0.0.0 --port 3002
```
Then use the API endpoint:
```bash
curl -X POST "http://localhost:3002/run-build-flow" \
     -H "Content-Type: application/json" \
     -d '{"yaml_text": "<your yaml here>", "input": "<your input here>"}'
```
- You can also use `/run-build-flow-async` for async execution.
- See the FastAPI docs for more endpoints and options.

### **Features**
- Supports stateful, multi-step flows
- Allows custom flow logic and branching
- Integrates with crews, agents, and tasks
- Can chain multiple crews and tasks in a single flow
- Can be run via CLI or FastAPI

---

## Advanced Tips

- **Environment Variables:**
  - You can use `${VAR_NAME}` in your YAML config to reference environment variables from your `.env` file. This is useful for secrets like API keys or credentials.
  - Example:
    ```yaml
    api_key: "${OPENAI_API_KEY}"
    ```
  - When the config is loaded, `${OPENAI_API_KEY}` will be replaced with the value from your `.env` file.

- **Custom Tools:**
  - For comprehensive guide on adding custom tools along with tool configuration and registration, see [`app/crewai/tools/README.md`](../../tools/README.md)
  - You can add your own tool classes in the `tools/` directory.
  - Register your tool in `tools/tools_registry.yaml` so it can be referenced in YAML configs.
  - For advanced MCP or Snowflake tool integration, see:
    - [`app/crewai/mcp/README.md`](../../mcp/README.md) and [`mcp_factory.py`](../../mcp/mcp_factory.py)
    - [`app/crewai/tools/snowflake_tools/README.md`](../../tools/snowflake_tools/README.md) and [`snowflake_tools_factory.py`](../../tools/snowflake_tools/snowflake_tools_factory.py)
  - Example:
    1. Create `tools/my_custom_tool.py` with your tool class.
    2. Add an entry to `tools_registry.yaml`:
       ```yaml
       MyCustomTool:
         implementation: "app.crewai.tools.my_custom_tool.MyCustomTool"
         config:
           param1: value1
       ```
    3. Reference `MyCustomTool` in your agent or task YAML.



---


