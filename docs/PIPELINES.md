# CI/CD Pipelines

This document describes the CI/CD pipelines for deploying BlendX to Snowflake Native App.

## Branch Flow

```
develop → qa → main (auto-tag) → production
```

| Branch/Action | Environment | Purpose |
|---------------|-------------|---------|
| `develop` | Local | Local development and testing (no CI) |
| `qa` | QA | Builds images, deploys to QA release channel |
| `main` | Production | Auto-creates release tag, triggers production deploy |

## Pipelines Overview

| Pipeline | File | Trigger | Purpose |
|----------|------|---------|---------|
| QA Deployment | `deploy-qa.yml` | Push to `qa` (merge from develop) | Build, deploy, and restart QA environment |
| Create Release Tag | `release.yml` | Push to `main` or manual | Auto-create release tag (auto-increment) |
| Production Release | `deploy-prod.yml` | Push tag `release/*` or manual | Promote QA version to production |

## QA Pipeline (deploy-qa.yml)

### Trigger

- **Automatic**: Push to `qa` branch (must be merged from `develop`)
- **Manual**: GitHub Actions workflow dispatch

### Preflight Validation

Before building, the pipeline validates:
- `qa` branch must contain all commits from `develop`
- `qa` must be updated via merge commit from `develop` (no direct commits)

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
9. **Upgrade & restart**: If app instance exists, upgrades and runs `manage-service.sh`
10. **Get URL**: Waits for service and retrieves application URL

### Version Strategy

- Version is derived from git tags: `v1.x.x` → `V1`, `v2.x.x` → `V2`
- Each push to `qa` adds a new patch to the current version
- Default version is `V1` if no tags exist

## Create Release Tag (release.yml)

### Trigger

- **Automatic**: Push to `main` branch (merge from qa)
- **Manual**: GitHub Actions workflow dispatch with optional version input

### Auto-increment

When triggered automatically (push to main), the tag version is auto-incremented:
- If no `release/*` tags exist: `release/v1.0.0`
- Otherwise: increments patch number (e.g., `release/v1.0.0` → `release/v1.0.1`)

### Manual Override

When triggered manually, you can specify:
- `version`: Release tag in format `release/vX.Y.Z` (leave empty for auto-increment)

### Validation

Before creating the tag:
- `main` must contain all commits from `qa`
- Tag must not already exist

### Output

Creates an annotated tag on `main` that triggers the production deployment.

## Production Pipeline (deploy-prod.yml)

### Trigger

- **Automatic**: Push tag matching `release/*`
- **Manual**: GitHub Actions workflow dispatch with optional version/patch inputs

### Validation

- If triggered by tag: verifies tag commit is on `main` branch

### Steps

1. **Auto-detect version**: Reads current version from QA release channel
2. **Verify version**: Confirms the version exists in the package
3. **Validate monotonicity**: Ensures we're not going backwards
4. **Add to DEFAULT channel**: Adds version to the DEFAULT (production) release channel
5. **Set release directive**: Points DEFAULT channel to the specified version/patch
6. **Show status**: Displays current versions and release directives

### Manual Override

When triggering manually, you can specify:
- `version`: Version to release (e.g., `V1`)
- `patch`: Patch number to release (e.g., `5`)

If not specified, values are auto-detected from QA channel.

## Manage Service Script (manage-service.sh)

Used by the QA pipeline to manage the SPCS service after deployment.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SNOWFLAKE_ROLE` | `BLENDX_APP_ROLE` | Role for executing commands |
| `SNOWFLAKE_APP_INSTANCE` | `BLENDX_APP_INSTANCE` | Application instance name |
| `SNOWFLAKE_COMPUTE_POOL` | `BLENDX_CP` | Compute pool for SPCS |
| `SNOWFLAKE_CONNECTION` | `mkt_blendx_demo` | Snowflake CLI connection name |

### Behavior

1. Checks if service exists and its status
2. If exists and SUSPENDED: Calls `resume_app()` procedure to resume service
3. If exists and running: Uses `ALTER SERVICE ... FORCE_PULL_IMAGE = TRUE` to pull new images
4. If not exists: Calls `start_app()` procedure to create service
5. Waits 30 seconds for startup
6. Shows service status and application URL

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
- **Updated by**: QA pipeline on every push to `qa`
- **Consumers**: QA app instance

### DEFAULT Channel

- **Purpose**: Production / Marketplace
- **Updated by**: Production pipeline on `release/*` tag
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
3. PR is merged to `develop`
4. When ready for QA: merge `develop` → `qa`
5. QA pipeline triggers → builds images, deploys, restarts service
6. QA testing is performed
7. When ready for release: merge `qa` → `main`
8. Release tag is auto-created (e.g., `release/v1.0.1`)
9. Tag triggers Production pipeline → promotes QA version to DEFAULT channel
10. Submit for Snowflake security review (manual step in Provider Studio)
11. After approval, version is available on Marketplace

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
