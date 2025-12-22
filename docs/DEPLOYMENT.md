# Automatic Deployment Guide

This guide explains how to set up and use the automatic CI/CD deployment pipeline for the BlendX Marketplace application.

## Branch Flow

```mermaid
flowchart LR
    subgraph Development
        A[develop] -->|merge| B[qa]
    end

    subgraph QA
        B -->|deploy-qa.yml| C[Build Images]
        C --> D[Deploy to QA Channel]
        D --> E[Upgrade App]
    end

    subgraph Production
        B -->|merge| F[main]
        F -->|release.yml| G[Create Tag]
        G -->|trigger| H[deploy-prod.yml]
        H --> I[Promote to DEFAULT]
    end

    style A fill:#e1f5fe
    style B fill:#fff3e0
    style F fill:#e8f5e9
    style I fill:#f3e5f5
```

### Pipeline Flow

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant GH as GitHub
    participant QA as QA Pipeline
    participant Rel as Release Pipeline
    participant Prod as Prod Pipeline
    participant SF as Snowflake

    Dev->>GH: merge develop → qa
    GH->>QA: trigger deploy-qa.yml
    QA->>SF: Build & push images
    QA->>SF: Register patch in QA channel
    QA->>SF: Upgrade application

    Dev->>GH: merge qa → main
    GH->>Rel: trigger release.yml
    Rel->>GH: create tag (release/vX.Y.Z)
    Rel->>Prod: trigger deploy-prod.yml
    Prod->>SF: Read QA version
    Prod->>SF: Promote to DEFAULT channel
```

| Branch | Environment | Purpose |
|--------|-------------|---------|
| `develop` | Local | Local development and testing (no CI) |
| `qa` | QA | Builds images, deploys to QA release channel (merge from develop) |
| `main` | Production | Auto-creates release tag, triggers production deploy (merge from qa) |

## Prerequisites

Before setting up automatic deployment, ensure you have:

1. A Snowflake account with ACCOUNTADMIN access (for initial setup)
2. Access to the GitHub repository settings
3. The Snowflake CLI installed locally (`snow`)

## Initial Setup (One-Time)

### Step 1: Generate RSA Key Pair

Generate the RSA keys for JWT authentication:

```bash
mkdir -p keys/pipeline
openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out keys/pipeline/snowflake_key.p8 -nocrypt
openssl rsa -in keys/pipeline/snowflake_key.p8 -pubout -out keys/pipeline/snowflake_key.pub
```

> **Important**: Keep `snowflake_key.p8` secure. This is your private key and should never be committed to the repository.

### Step 2: Run Provider Setup Script

The setup script creates the CI/CD user, role, and necessary permissions in Snowflake:

```bash
# Ensure you have a connection with ACCOUNTADMIN role configured
./scripts/provider-setup.sh
```

The script will:
1. Create a service user (`MK_BLENDX_DEPLOY_USER`) with JWT authentication
2. Create a role (`MK_BLENDX_DEPLOY_ROLE`) with necessary permissions
3. Grant permissions on warehouse, database, schema, stage, and image repository
4. Grant permission to create Application Packages
5. Optionally create the Application Package

### Step 3: Configure GitHub Secrets

In your GitHub repository, go to **Settings > Secrets and variables > Actions** and create two environments:

#### Environment: `qa`

| Secret | Description | Example |
|--------|-------------|---------|
| `SNOWFLAKE_ACCOUNT` | Snowflake account identifier | `xy12345.us-east-1` |
| `SNOWFLAKE_HOST` | Snowflake host URL | `xy12345.us-east-1.snowflakecomputing.com` |
| `SNOWFLAKE_DEPLOY_USER` | CI/CD user name | `MK_BLENDX_DEPLOY_USER` |
| `SNOWFLAKE_DEPLOY_ROLE` | CI/CD role name | `MK_BLENDX_DEPLOY_ROLE` |
| `SNOWFLAKE_WAREHOUSE` | Warehouse name | `DEV_WH` |
| `SNOWFLAKE_DATABASE` | Database name | `SPCS_APP_TEST` |
| `SNOWFLAKE_SCHEMA` | Schema name | `NAPP` |
| `SNOWFLAKE_PRIVATE_KEY_RAW` | Content of `snowflake_key.p8` | (full PEM content) |
| `SNOWFLAKE_REPO` | Image repository URL | `xy12345.registry.snowflakecomputing.com/spcs_app_test/napp/img_repo` |
| `SNOWFLAKE_APP_PACKAGE` | Application package name | `MK_BLENDX_APP_PKG` |
| `SNOWFLAKE_APP_INSTANCE` | Installed app instance name | `BLENDX_APP` |
| `SNOWFLAKE_COMPUTE_POOL` | Compute pool for the app | `MY_COMPUTE_POOL` |
| `SNOWFLAKE_ROLE` | Role for app management | `nac_test` |

#### Environment: `production`

Configure the same secrets for production, potentially with different values for production resources.

### Step 4: Get the Private Key Content

To copy the private key content for the GitHub secret:

```bash
cat keys/pipeline/snowflake_key.p8
```

Copy the **entire content** including the `-----BEGIN PRIVATE KEY-----` and `-----END PRIVATE KEY-----` headers.

## Pipelines Overview

| Pipeline | File | Trigger | Purpose |
|----------|------|---------|---------|
| QA Deployment | `deploy-qa.yml` | Push to `qa` (merge from develop) | Build, deploy, and restart QA environment |
| Create Release Tag | `release.yml` | Push to `main` or manual | Auto-create release tag and trigger production deploy |
| Production Release | `deploy-prod.yml` | Called by `release.yml` or manual | Promote QA version to production |

## QA Pipeline (deploy-qa.yml)

### Trigger

- **Automatic**: Push to `qa` branch (must be merged from `develop`)
- **Manual**: GitHub Actions workflow dispatch

### Preflight Validation

Before building, the pipeline validates:
- `qa` branch must contain all commits from `develop`
- `qa` must be updated via merge commit from `develop` (no direct commits)

### Steps

1. Validates that `qa` was updated via a merge from `develop`
2. Builds Docker images for backend, frontend, and router (parallel)
3. Pushes images to Snowflake Image Repository
4. Generates `setup.sql` from templates
5. Uploads application files to Snowflake stage
6. Creates the Application Package if it doesn't exist
7. Registers a new patch in the QA release channel
8. Upgrades and restarts the application (if installed)

### Version Strategy

- Version is derived from git tags: `v1.x.x` → `V1`, `v2.x.x` → `V2`
- Each push to `qa` adds a new patch to the current version
- Default version is `V1` if no tags exist

## Release Tag Pipeline (release.yml)

### Trigger

- **Automatic**: Push to `main` branch (merge from qa)
- **Manual**: GitHub Actions workflow dispatch with optional version input

### Auto-increment

When triggered automatically (push to main), the tag version is auto-incremented:
- If no `release/*` tags exist: `release/v1.0.0`
- Otherwise: increments patch number (e.g., `release/v1.0.0` → `release/v1.0.1`)

### Output

Creates an annotated tag on `main` and directly triggers the `deploy-prod.yml` workflow via `workflow_dispatch`.

## Production Pipeline (deploy-prod.yml)

### Trigger

- **Automatic**: Called by `release.yml` after creating the tag
- **Manual**: GitHub Actions workflow dispatch with optional version/patch inputs

### Steps

1. Reads the latest version and patch from the QA release channel
2. Validates the promotion is monotonic (no regressions)
3. Promotes the QA version to the DEFAULT (production) release channel
4. Sets the DEFAULT release directive

### Manual Override

When triggering manually, you can specify:
- `version`: Version to release (e.g., `V1`)
- `patch`: Patch number to release (e.g., `5`)

If not specified, values are auto-detected from QA channel.

## Release Channels

| Channel | Purpose | Updated by |
|---------|---------|------------|
| `QA` | Testing and development | QA pipeline on every push to `qa` |
| `DEFAULT` | Production (marketplace consumers) | Production pipeline (triggered by `release.yml`) |

> **Note**: Versions in DEFAULT channel require Snowflake security review before they are available to marketplace consumers.

## Typical Workflow

1. Developer creates feature branch from `develop`
2. Developer creates PR to `develop`
3. PR is merged to `develop`
4. When ready for QA: merge `develop` → `qa`
5. QA pipeline triggers → builds images, deploys, restarts service
6. QA testing is performed
7. When ready for release: merge `qa` → `main`
8. Release tag is auto-created (e.g., `release/v1.0.1`)
9. Production pipeline is triggered → promotes QA version to DEFAULT channel
10. Submit for Snowflake security review (manual step in Provider Studio)
11. After approval, version is available on Marketplace

## Troubleshooting

### Connection Test Fails

If the Snowflake connection test fails:

1. Verify the public key is correctly set for the user:
   ```sql
   DESCRIBE USER MK_BLENDX_DEPLOY_USER;
   ```

2. Check if the role has necessary permissions:
   ```sql
   SHOW GRANTS TO ROLE MK_BLENDX_DEPLOY_ROLE;
   ```

3. Ensure the schema exists and is accessible

### Permission Denied Errors

If you get permission errors:

1. Re-run the provider setup script:
   ```bash
   ./scripts/provider-setup.sh
   ```

2. Verify the role is being used:
   ```sql
   USE ROLE MK_BLENDX_DEPLOY_ROLE;
   SHOW GRANTS TO ROLE MK_BLENDX_DEPLOY_ROLE;
   ```

### Application Package Creation Fails

If the Application Package creation fails:

1. Ensure the role has `CREATE APPLICATION PACKAGE ON ACCOUNT`:
   ```sql
   GRANT CREATE APPLICATION PACKAGE ON ACCOUNT TO ROLE MK_BLENDX_DEPLOY_ROLE;
   ```

### Docker Push Fails

If Docker image push fails:

1. Verify image repository permissions:
   ```sql
   GRANT READ, WRITE ON IMAGE REPOSITORY SPCS_APP_TEST.NAPP.img_repo TO ROLE MK_BLENDX_DEPLOY_ROLE;
   ```

2. Check the `SNOWFLAKE_REPO` secret format matches your image repository URL

### Build Takes Too Long

- Docker builds use GHA cache with separate scopes per image
- First build will be slow, subsequent builds use cache
- Backend image is typically the slowest due to Python dependencies

### Service Not Restarting

- Check if `SNOWFLAKE_APP_INSTANCE` secret is set correctly
- Verify the application exists with `SHOW APPLICATIONS`
- Check service logs with `get_service_logs()` procedure

### Version Conflicts

- Snowflake allows max 2 versions not in any release channel
- Pipeline automatically cleans up orphan versions
- If issues persist, manually deregister old versions

### Application Not Found

- Ensure the application was created with `setup/create-application.sh`
- Verify the `SNOWFLAKE_ROLE` has access to the application
- Check that `SNOWFLAKE_APP_INSTANCE` matches the actual app name

## Security Considerations

1. **Private Key**: Never commit `snowflake_key.p8` to the repository
2. **GitHub Secrets**: Use environment-specific secrets for different environments
3. **Least Privilege**: The CI/CD role only has permissions it needs
4. **Service User**: The CI/CD user is a `SERVICE` type user without interactive login

## Files Reference

| File | Purpose |
|------|---------|
| `.github/workflows/deploy-qa.yml` | QA deployment workflow |
| `.github/workflows/release.yml` | Auto-creates release tags and triggers production deploy |
| `.github/workflows/deploy-prod.yml` | Production promotion workflow (QA → DEFAULT) |
| `scripts/provider-setup.sh` | Initial setup script |
| `scripts/sql/setup_cicd_permissions.sql` | SQL permissions reference |
