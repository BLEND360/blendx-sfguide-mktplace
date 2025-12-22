# Automatic Deployment Guide

This guide explains how to set up and use the automatic CI/CD deployment pipeline for the BlendX Marketplace application.

## Overview

The deployment pipeline follows a strict branch promotion flow:

```
develop → qa → main (auto-tag) → production
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

## How the Pipeline Works

### Local Development (`develop` branch)

The `develop` branch is used for local development and testing. No automatic deployment is triggered when pushing to this branch. Use this branch to develop and test changes locally before pushing to QA.

### QA Deployment (`qa` branch)

When you push to `qa`, the pipeline:

1. Validates that `qa` was updated via a merge from `develop`
2. Determines the QA version (fixed major version, patch-based)
3. Builds Docker images for backend, frontend, and router
4. Pushes images to Snowflake Image Repository
5. Generates `setup.sql` from templates
6. Uploads application files to Snowflake stage
7. Creates the Application Package if it doesn't exist
8. Registers a new patch in the QA release channel
9. Restarts the application (if installed)

### Production Release (`main` branch)

When you merge `qa` into `main`:

1. The `release.yml` workflow automatically creates a release tag (e.g., `release/v1.0.1`)
2. The tag triggers the `deploy-prod.yml` workflow
3. The production pipeline:
   - Verifies the tag is on the `main` branch
   - Reads the latest version and patch from the QA release channel
   - Validates the promotion is monotonic (no regressions)
   - Promotes the QA version to the DEFAULT (production) release channel
   - Sets the DEFAULT release directive

## Versioning Model

The deployment pipeline uses a strict separation between QA and Production:

- **QA**
  - Uses a fixed major version (e.g. `V1`)
  - Each deployment creates a new patch
  - QA is the single source of truth for production

- **Production**
  - Auto-incremented release tags (`release/vX.Y.Z`)
  - Tags are created automatically on merge to `main`
  - Production always promotes the latest QA patch

## Manual Triggers

Both pipelines can be triggered manually from GitHub Actions:

1. Go to **Actions** tab in GitHub
2. Select the workflow
3. Click **Run workflow**

For production releases, you can optionally specify version and patch numbers.

## Release Channels

The pipeline uses Snowflake release channels:

| Channel | Purpose |
|---------|---------|
| `QA` | Testing and development |
| `DEFAULT` | Production (marketplace consumers) |


## Release Flow Summary

1. Develop features on `develop`
2. Merge `develop` → `qa`
3. QA pipeline deploys and validates changes
4. Merge `qa` → `main`
5. Release tag is auto-created (e.g., `release/v1.0.1`)
6. Production pipeline promotes QA → DEFAULT

This flow guarantees:
- No direct deployments from development branches
- Full auditability of production releases
- Strong separation between build, validation, and release

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

## Security Considerations

1. **Private Key**: Never commit `snowflake_key.p8` to the repository
2. **GitHub Secrets**: Use environment-specific secrets for different environments
3. **Least Privilege**: The CI/CD role only has permissions it needs
4. **Service User**: The CI/CD user is a `SERVICE` type user without interactive login

## Files Reference

| File | Purpose |
|------|---------|
| `.github/workflows/deploy-qa.yml` | QA deployment workflow |
| `.github/workflows/release.yml` | Auto-creates release tags on merge to main |
| `.github/workflows/deploy-prod.yml` | Production promotion workflow (QA → DEFAULT) |
| `scripts/provider-setup.sh` | Initial setup script |
| `scripts/sql/setup_cicd_permissions.sql` | SQL permissions reference |
