# BlendX - AI Workflow Platform

Build and execute AI workflows using natural language.

## Features

### Generate Workflows
Describe your workflow in natural language and get:
- **YAML Configuration** - Complete CrewAI workflow definition
- **Rationale** - Explanation of design decisions
- **Diagram** - Visual Mermaid representation

### Manage Workflows
- **History** - Browse and search saved workflows
- **Save** - Store workflows with custom titles
- **Details** - View Rationale, YAML, and Diagram tabs

### Execute Workflows
- **Run Workflow** - Execute with optional input data
- **List Executions** - View all executions for a workflow
- **View Results** - See execution output or error details

### System Tests
Verify connectivity:
- Test Cortex, LiteLLM, Secrets, Serper

## How to Use

### Generate a Workflow
1. Type a description in the chat
2. Press `Ctrl+Enter` or click **Send**
3. View results in Rationale/YAML/Diagram tabs
4. Click **Save** to store

### View Workflow History
1. Click **Load History**
2. Select a workflow card
3. Use **List Executions** or **Run Workflow**

### View Executions
1. From workflow details, click **List Executions**
2. View status table (ID, Status, Timestamps)
3. Click **View** to see full results

## Status Colors

| Color | Status |
|-------|--------|
| Green | COMPLETED |
| Blue | PROCESSING |
| Orange | PENDING |
| Red | ERROR |
