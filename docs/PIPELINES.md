# CI/CD Pipelines

This document describes the CI/CD pipelines for deploying BlendX to Snowflake Native App.

## Pipelines Overview

| Pipeline | File | Trigger | Purpose |
|----------|------|---------|---------|
| QA Deployment | `deploy-qa.yml` | Push to `develop` or manual | Build, deploy, and restart QA environment |
| Production Release | `release-prod.yml` | Push to `main` or manual | Promote QA version to production |

## QA Pipeline (deploy-qa.yml)

### Trigger

- **Automatic**: Push to `develop` branch
- **Manual**: GitHub Actions workflow dispatch

### Jobs

The pipeline consists of 4 jobs:

#### 1. build-backend (parallel)

Builds and pushes the FastAPI backend Docker image to Snowflake registry.

- Checkout code
- Setup Docker Buildx with GHA cache
- Install and configure Snowflake CLI with JWT authentication
- Login to Snowflake Docker registry
- Build and push `eap_backend` image

#### 2. build-frontend (parallel)

Builds and pushes the Vue.js frontend Docker image to Snowflake registry.

- Same setup steps as backend
- Build and push `eap_frontend` image

#### 3. build-router (parallel)

Builds and pushes the Nginx router Docker image to Snowflake registry.

- Same setup steps as backend
- Build and push `eap_router` image

#### 4. deploy (sequential, after builds)

Deploys the application package and restarts the service.

**Steps:**

1. **Determine version**: Extracts version from git tags (e.g., `v1.0.0` → `V1`)
2. **Generate manifest.yml**: Creates manifest from template with environment-specific values
3. **Generate setup.sql**: Combines table definitions with setup template
4. **Upload to stage**: Uploads all app files to Snowflake stage
5. **Create package**: Creates Application Package if not exists
6. **Clean up versions**: Removes orphan versions not in any release channel
7. **Register version/patch**: Registers new version or adds patch to existing version
8. **Update QA channel**: Sets the release directive for QA channel
9. **Upgrade & restart**: If app instance exists, upgrades and runs `restart.sh`
10. **Get URL**: Waits for service and retrieves application URL

### Version Strategy

- Version is derived from git tags: `v1.x.x` → `V1`, `v2.x.x` → `V2`
- Each push to develop adds a new patch to the current version
- Default version is `V1` if no tags exist

## Production Pipeline (release-prod.yml)

### Trigger

- **Automatic**: Push to `main` branch
- **Manual**: GitHub Actions workflow dispatch with optional version/patch inputs

### Steps

1. **Auto-detect version**: Reads current version from QA release channel
2. **Verify version**: Confirms the version exists in the package
3. **Add to DEFAULT channel**: Adds version to the DEFAULT (production) release channel
4. **Set release directive**: Points DEFAULT channel to the specified version/patch
5. **Show status**: Displays current versions and release directives

### Manual Override

When triggering manually, you can specify:
- `version`: Version to release (e.g., `V1`)
- `patch`: Patch number to release (e.g., `5`)

If not specified, values are auto-detected from QA channel.

## Restart Script (restart.sh)

Used by the QA pipeline to restart the SPCS service after deployment.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SNOWFLAKE_ROLE` | `BLENDX_APP_ROLE` | Role for executing commands |
| `SNOWFLAKE_APP_INSTANCE` | `BLENDX_APP_INSTANCE` | Application instance name |
| `SNOWFLAKE_COMPUTE_POOL` | `BLENDX_CP` | Compute pool for SPCS |
| `SNOWFLAKE_CONNECTION` | `mkt_blendx_demo` | Snowflake CLI connection name |

### Behavior

1. Checks if service exists
2. If exists: Uses `ALTER SERVICE ... FORCE_PULL_IMAGE = TRUE` to pull new images
3. If not exists: Calls `start_app()` procedure to create service
4. Waits 30 seconds for startup
5. Shows service status and application URL

## GitHub Secrets Required

### QA Environment

| Secret | Description |
|--------|-------------|
| `SNOWFLAKE_ACCOUNT` | Snowflake account identifier |
| `SNOWFLAKE_HOST` | Snowflake host URL |
| `SNOWFLAKE_DEPLOY_USER` | CI/CD user for deployment |
| `SNOWFLAKE_DEPLOY_ROLE` | Role for package management |
| `SNOWFLAKE_ROLE` | Role for app instance management |
| `SNOWFLAKE_WAREHOUSE` | Warehouse for SQL operations |
| `SNOWFLAKE_DATABASE` | Database containing stage |
| `SNOWFLAKE_SCHEMA` | Schema containing stage |
| `SNOWFLAKE_PRIVATE_KEY_RAW` | JWT private key (raw content) |
| `SNOWFLAKE_REPO` | Docker registry URL |
| `SNOWFLAKE_APP_PACKAGE` | Application package name |
| `SNOWFLAKE_APP_INSTANCE` | QA app instance name |
| `SNOWFLAKE_COMPUTE_POOL` | Compute pool for SPCS |

### Production Environment

Same secrets as QA, typically pointing to production resources.

## Release Channels

### QA Channel

- **Purpose**: Internal testing
- **Updated by**: QA pipeline on every push to `develop`
- **Consumers**: QA app instance

### DEFAULT Channel

- **Purpose**: Production / Marketplace
- **Updated by**: Production pipeline on push to `main`
- **Consumers**: Marketplace consumers
- **Note**: Versions in DEFAULT channel require Snowflake security review

## Docker Images

| Image | Source | Description |
|-------|--------|-------------|
| `eap_backend` | `./backend` | FastAPI + CrewAI backend |
| `eap_frontend` | `./frontend` | Vue.js frontend |
| `eap_router` | `./router` | Nginx reverse proxy |

All images are:
- Built for `linux/amd64` platform
- Cached using GitHub Actions cache
- Pushed to Snowflake's Docker registry

## Typical Workflow

1. Developer creates feature branch from `develop`
2. Developer creates PR to `develop`
3. PR is merged → QA pipeline triggers
4. QA pipeline builds images in parallel, deploys, restarts service
5. QA testing is performed
6. When ready, create PR from `develop` to `main`
7. PR is merged → Production pipeline triggers
8. Production pipeline promotes QA version to DEFAULT channel
9. Submit for Snowflake security review (manual step)
10. After approval, version is available on Marketplace

## Troubleshooting

### Build takes too long

- Docker builds use GHA cache with separate scopes per image
- First build will be slow, subsequent builds use cache
- Backend image is typically the slowest due to Python dependencies

### Service not restarting

- Check if `SNOWFLAKE_APP_INSTANCE` secret is set correctly
- Verify the application exists with `SHOW APPLICATIONS`
- Check service logs with `get_service_logs()` procedure

### Version conflicts

- Snowflake allows max 2 versions not in any release channel
- Pipeline automatically cleans up orphan versions
- If issues persist, manually deregister old versions

### Application not found

- Ensure the application was created with `setup/create-application.sh`
- Verify the `SNOWFLAKE_ROLE` has access to the application
- Check that `SNOWFLAKE_APP_INSTANCE` matches the actual app name
