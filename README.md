# BlendX - AI Workflow Platform

BlendX is a native Snowflake application that enables you to build and execute AI workflows using CrewAI.

## Features

- **Workflow Generator**: Create AI workflows from natural language descriptions
- **Workflow Management**: Save, browse, and manage workflow history
- **Workflow Execution**: Run workflows with real-time monitoring
- **System Diagnostics**: Verify Cortex, LiteLLM, and external API connections

## Quick Start

### Local Development

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with your Snowflake credentials and API keys

# 2. Start services
docker-compose up

# 3. Access the application
open http://localhost:8000
```

See [docs/LOCAL_DEVELOPMENT.md](docs/LOCAL_DEVELOPMENT.md) for detailed instructions.

### Production Deployment

For deploying to Snowflake as a Native App, see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Documentation

| Document | Description |
|----------|-------------|
| [LOCAL_DEVELOPMENT.md](docs/LOCAL_DEVELOPMENT.md) | Local development setup and workflow |
| [DEPLOYMENT.md](docs/DEPLOYMENT.md) | CI/CD pipelines and production deployment |
| [MONITORING.md](docs/MONITORING.md) | Service monitoring and troubleshooting |
| [LIMITATIONS.md](docs/LIMITATIONS.md) | Known limitations and workarounds |
| [BlendX_Documentation.md](docs/BlendX_Documentation.md) | Full application documentation |

## Project Structure

```
blendx-sfguide-mktplace/
├── backend/               # FastAPI backend
├── frontend/              # Vue.js frontend
├── scripts/               # Deployment and generation scripts
│   ├── generate/          # Code generation scripts
│   ├── generated/         # Auto-generated files
│   └── deploy/            # Deployment scripts
├── templates/             # Application templates
├── setup/                 # Initial setup scripts
└── docs/                  # Documentation
```

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Snowflake CLI](https://docs.snowflake.com/en/developer-guide/snowflake-cli-v2/index) (for deployment)

## License

Proprietary - All rights reserved.
