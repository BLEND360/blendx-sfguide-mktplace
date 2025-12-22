# TODO List - Snowflake Marketplace App Template

> Objective: Transform this project into a reusable template for any Snowflake Marketplace application.

## Base Template Architecture

By default, the template includes:
- **Backend** (Python/FastAPI)
- **Frontend** (Vue.js)
- **Router** (NGINX reverse proxy)

All containers communicate with each other through the router.

---

## Already Implemented (Validate / Improve)

| # | Item | Status | Location |
|---|------|--------|----------|
| 1 | Manifest template | ✅ Exists | `templates/manifest_template.yml` |
| 2 | Setup SQL template | ✅ Exists | `templates/setup_template.sql` |
| 3 | Dockerfiles (backend/frontend/router) | ✅ Exists | Needs further templating |
| 4 | CI/CD pipelines (QA/Prod) | ✅ Exists | `.github/workflows/` |
| 5 | External Access Integration | ✅ Partial | Improve with modular templates |
| 6 | Basic secret management | ✅ Partial | Uses env vars and GitHub secrets |
| 7 | Deployment docs | ✅ Exists | `docs/DEPLOYMENT.md` |
| 8 | Local development guide | ✅ Exists | `docs/LOCAL_DEVELOPMENT.md` |

---

## To Be Implemented

### 1. DB Migrations

- [ ] Versioned SQL migration system (`migrations/V001__initial.sql`)
- [ ] Script to automatically apply migrations in CI/CD
- [ ] Migration rollback support
- [ ] Applied schema version tracking
- [ ] Empty migration template for new changes

---

### 2. Autoscale Compute Pool

- [ ] Compute pool template with autoscaling (`templates/compute_pool_template.sql`)
- [ ] Parametrized MIN/MAX node configuration
- [ ] Metric-based scaling policies
- [ ] Compute pool configuration documentation
- [ ] Examples for different sizes (small/medium/large)

---

### 3. Advanced Logging

- [ ] Integration with Snowflake Event Tables
- [ ] Structured log forwarding (JSON)
- [ ] Environment-based log level configuration
- [ ] Dashboards / queries for log analysis
- [ ] Event table template

---

### 4. Usage Tracking (CPU / Memory)

- [ ] Queries to monitor compute pool usage
- [ ] Excessive usage alerts
- [ ] Metrics dashboard
- [ ] Historical consumption for billing
- [ ] Usage reporting script

---

### 5. Secret Management

#### CI/CD Pipeline Secrets

- [ ] Complete documentation of required GitHub secrets
- [ ] List of all secrets needed for deploy pipelines (QA/Prod)
- [ ] Secret rotation guide for CI/CD credentials
- [ ] Validation script to check pipeline secrets before deploy

#### App Secrets (Consumer Configuration)

- [ ] Documentation with screenshots of Snowflake UI for secret setup
- [ ] Example manifest configuration for secrets (`references` section)
- [ ] Template showing how to declare required secrets in manifest
- [ ] Guide explaining the consumer flow (install → configure secrets → use app)

---

### 6. External Access Integration (EAI)

#### Modular EAI Templates

- [ ] `templates/eai/external_access_template.sql` - Base template
- [ ] `templates/eai/network_rule_template.sql` - Network rules
- [ ] `templates/eai/secret_template.sql` - External API secrets
- [ ] Flag in `setup_template.sql` to include/exclude EAI
- [ ] Documentation on when and how to use EAI

#### Preconfigured Examples

- [ ] EAI for generic REST APIs
- [ ] EAI for OpenAI / LLM providers
- [ ] EAI for webhooks
- [ ] EAI for external storage services

#### Documentation

- [ ] `docs/EXTERNAL_ACCESS.md` - Complete EAI guide
- [ ] Configuration flow diagram
- [ ] Common EAI error troubleshooting
- [ ] EAI security checklist

---

### 7. Add Container Script

#### Container Bootstrap Script

- [ ] `scripts/add-container.sh` - Interactive script to add a new container

```bash
./scripts/add-container.sh --name api-worker --port 8082 --type python
```

- [ ] Automatically generates:
  - [ ] `{container_name}/Dockerfile` from template
  - [ ] Entry in `docker-compose.yml`
  - [ ] Configuration in `router/nginx.conf`
  - [ ] Entry in `templates/fullstack_template.yaml`
  - [ ] Environment variables in `.env.example`
  - [ ] CI/CD entry (build job)

#### Container Templates

- [ ] `templates/containers/python/Dockerfile.template` (base)
- [ ] `templates/containers/python/Dockerfile.uv.template` (uv-based)
- [ ] `templates/containers/python/Dockerfile.poetry.template` (poetry-based)
- [ ] `templates/containers/node/Dockerfile.template`
- [ ] `templates/containers/node/Dockerfile.pnpm.template` (pnpm-based)
- [ ] `templates/containers/go/Dockerfile.template`
- [ ] `templates/containers/nginx.location.template` (router)

#### Automations

- [ ] Auto-registration in the router (`nginx.conf`)
- [ ] Auto-registration in `docker-compose.yml`
- [ ] Auto-registration in `fullstack_template.yaml`
- [ ] Auto-registration in CI/CD pipelines
- [ ] Default health check endpoint
- [ ] Available port validation

#### Additional Commands

- [ ] `scripts/remove-container.sh` - Remove container
- [ ] `scripts/list-containers.sh` - List existing containers

---

### 8. Provider Instructions

- [ ] `docs/PROVIDER_SETUP.md` - Step-by-step guide
- [ ] Prerequisites checklist
- [ ] `scripts/provider-init.sh` - Automated setup script
- [ ] Troubleshooting guide
- [ ] Provider architecture diagram

---

### 9. Consumer Instructions

- [ ] `docs/CONSUMER_GUIDE.md` - Installation guide
- [ ] Post-installation configuration
- [ ] Common issues FAQ
- [ ] Videos / screenshots of the process
- [ ] Parametrized `consumer_setup.sql` template

---

### 10. Dockerfile Templates

- [ ] Base Dockerfile parametrized by language
- [ ] Optimized multi-stage builds
- [ ] Documented best practices
- [ ] Configurable ARG / ENV
- [ ] Default health check included

#### Python Package Manager Support

- [ ] Support for `uv` based projects (`pyproject.toml` + `uv.lock`)
- [ ] Support for traditional `pip` + `requirements.txt`
- [ ] Support for `poetry` based projects
- [ ] Auto-detection of package manager from project files
- [ ] Template flag to select package manager: `--pkg-manager [uv|pip|poetry]`

#### UV-Specific Optimizations

- [ ] Multi-stage build with `uv` for faster dependency resolution
- [ ] Cached `uv` layers for faster rebuilds
- [ ] `uv sync --frozen` for reproducible builds
- [ ] Support for `uv` workspaces (monorepo)
- [ ] Documentation on migrating from pip/poetry to uv

---

### 11. How to Run Locally Guide

- [ ] Improve `docs/LOCAL_DEVELOPMENT.md`
- [ ] `scripts/local-setup.sh` - One-line setup
- [ ] Snowflake service mocks for local testing
- [ ] Hot-reload enabled by default
- [ ] Debugging instructions

---

### 12. Marketplace Listing Checklist

Create `checklists/marketplace_listing.md` with all required fields:

#### Basic Information

- [ ] App Name
- [ ] Short Description (≤100 chars)
- [ ] Full Description (≤4000 chars)
- [ ] Category
- [ ] Subcategory
- [ ] Tags / Keywords

#### Branding

- [ ] Logo (512x512 PNG)
- [ ] Banner Image (1200x400)
- [ ] Screenshots (min 3, max 10)
- [ ] Demo Video URL (optional)

#### Documentation Links

- [ ] Documentation URL
- [ ] Support URL
- [ ] Privacy Policy URL
- [ ] Terms of Service URL
- [ ] Release Notes URL

#### Technical Details

- [ ] Minimum Snowflake Edition
- [ ] Required Privileges
- [ ] External Access Requirements
- [ ] Estimated Resource Usage
- [ ] Supported Regions
- [ ] Supported Cloud Providers (AWS / Azure / GCP)

#### Pricing

- [ ] Pricing Model (Free / Paid / Free Trial)
- [ ] Monthly price (if paid)
- [ ] Trial duration (if applicable)
- [ ] Usage-based pricing details

#### Support

- [ ] Support Email
- [ ] Support Hours
- [ ] SLA (if applicable)
- [ ] Response Time Commitment

#### Compliance & Security

- [ ] Security Review Completed
- [ ] Data Handling Documentation
- [ ] GDPR Compliance (if applicable)
- [ ] SOC2 Compliance (if applicable)
- [ ] Data Residency Requirements

#### Release Information

- [ ] Initial Version
- [ ] Release Date
- [ ] Changelog documented

---

### 13. Testing Framework

- [ ] Integration tests for the native app
- [ ] Post-deployment smoke tests
- [ ] Automatic privilege validation
- [ ] Container connectivity tests

---

### 14. Versioning Strategy

- [ ] Automated semantic versioning
- [ ] Automatic changelog generation
- [ ] Release notes template
- [ ] Version bump script

---

### 15. Advanced Health Checks

- [ ] Complete health check endpoints (`/health`, `/ready`, `/live`)
- [ ] Snowflake connectivity verification
- [ ] External dependency status
- [ ] Health check integrated into the router

---

### 16. Configuration Management

- [ ] `.env` template with all variables documented
- [ ] Startup configuration validation
- [ ] Improved `configure.sh` (interactive wizard)
- [ ] Automatic `.env` generation from template

---

### 17. Security Hardening

- [ ] `checklists/security_review.md`
- [ ] CI/CD vulnerability scanning
- [ ] OWASP guidelines checklist
- [ ] Dependabot / Renovate configured

---

### 18. Consumer Onboarding Automation

- [ ] First-time consumer setup script
- [ ] Interactive configuration wizard
- [ ] Full setup validation
- [ ] Welcome message / in-app tutorial

---

### 29. QA Pipeline Enhancements

- [ ] Execute unit tests automatically in QA pipeline
- [ ] Run linter checks (Python, JavaScript/TypeScript) in QA pipeline
- [ ] Pre-commit hooks configured for repo (black, isort, eslint, prettier)
- [ ] Enforce code style and quality gates before merge
- [ ] Report unit test results in pipeline dashboard
- [ ] Fail QA pipeline if any tests or lint checks fail

---

### 30. Container Resource Monitoring

- [ ] Track CPU usage per container
- [ ] Track memory usage per container
- [ ] Collect container metrics into a central dashboard
- [ ] Alert on resource thresholds (high CPU/memory)
- [ ] Historical resource usage reports for cost analysis
- [ ] Optional automatic scaling or throttling based on metrics

---

### 31. Generic Makefile with Useful Commands

- [ ] Create a `Makefile` with common development and deployment commands
- [ ] Include commands for running tests (unit, integration)
- [ ] Add command to start the app locally (backend and frontend)
- [ ] Add commands to validate linters and formatters
- [ ] Include commands to run DB migration scripts
- [ ] Add commands for building and pushing Docker images
- [ ] Provide commands for cleaning build artifacts and caches
- [ ] Document usage of each Makefile command in README or separate doc

---

## Proposed Template Structure

```text
marketplace-app-template/
├── .github/
│   └── workflows/
│       ├── deploy-qa.yml
│       └── deploy-prod.yml
├── app/
│   └── src/                    # Generated files
├── backend/                    # Default backend container
│   ├── Dockerfile
│   └── app/
├── frontend/                   # Default frontend container
│   ├── Dockerfile
│   └── src/
├── router/                     # NGINX reverse proxy
│   ├── Dockerfile
│   └── nginx.conf
├── scripts/
│   ├── sql/
│   │   └── migrations/         # DB migrations
│   ├── add-container.sh
│   ├── remove-container.sh
│   ├── list-containers.sh
│   ├── provider-init.sh
│   └── local-setup.sh
├── templates/
│   ├── manifest_template.yml
│   ├── setup_template.sql
│   ├── fullstack_template.yaml
│   ├── compute_pool_template.sql
│   ├── eai/
│   │   ├── external_access_template.sql
│   │   ├── network_rule_template.sql
│   │   └── secret_template.sql
│   └── containers/
│       ├── python/
│       │   ├── Dockerfile.template
│       │   ├── Dockerfile.uv.template
│       │   └── Dockerfile.poetry.template
│       ├── node/
│       │   ├── Dockerfile.template
│       │   └── Dockerfile.pnpm.template
│       ├── go/
│       │   └── Dockerfile.template
│       └── nginx.location.template
├── docs/
│   ├── PROVIDER_SETUP.md
│   ├── CONSUMER_GUIDE.md
│   ├── EXTERNAL_ACCESS.md
│   ├── MONITORING.md
│   ├── DEPLOYMENT.md
│   └── LOCAL_DEVELOPMENT.md
├── checklists/
│   ├── marketplace_listing.md
│   ├── security_review.md
│   └── pre_release.md
├── docker-compose.yml
├── Makefile
├── configure.sh
├── .env.example
└── README.md
```

---

## Summary

| Category | Items |
|---------|-------|
| Base Infrastructure (existing) | 8 |
| DB Migrations | 5 |
| Autoscale Compute Pool | 5 |
| Logging | 5 |
| Usage Tracking | 5 |
| Secret Management | 8 |
| External Access Integration | 13 |
| Add Container Script | 18 |
| Provider / Consumer Docs | 10 |
| Dockerfile Templates | 15 |
| Local Development | 5 |
| Marketplace Listing Checklist | 25+ |
| Testing / Versioning / Security | 15 |
| Makefile Commands | 8 |

---

## Notes

- Items marked with ✅ already exist but may require improvements to be more generic / templated.
- Implementation priority may vary depending on project needs.
- This document should be updated as items are completed.
