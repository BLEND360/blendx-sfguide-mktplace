# BlendX Deployment Scripts

This directory contains scripts for deploying the BlendX Native Application to Snowflake.

## Prerequisites

- Snowflake CLI (`snow`) installed and configured
- Docker installed and running
- Appropriate Snowflake roles and permissions
- `.env` file configured (see `.env.example`)

## Initial Setup Workflow

### Provider (Application Publisher)

The provider is responsible for creating and deploying the application package.

#### Step 1: Create Application Package

```bash
./scripts/provider-setup.sh
```

This script:
- Creates the application package in Snowflake
- Grants INSTALL and DEVELOP privileges to the consumer role

#### Step 2: Build and Deploy

```bash
./scripts/deploy.sh --setup-mode
```

This script:
- Builds Docker images for backend, frontend, and router
- Pushes images to Snowflake registry
- Uploads application files to Snowflake stage
- Registers the application version

### Consumer (Application Installer)

The consumer is responsible for setting up secrets and creating the application instance.


#### Step 3: Create Application Instance

```bash
./scripts/create-application.sh
```

This script:
- Creates the application instance from the package
- Configures secret references
- Starts the SPCS service
- Displays service status

#### Step 4: Setup Secrets, Permissions, and External Access

```bash
snow sql -f scripts/sql/consumer.sql --connection mkt_blendx_demo
```

Before running, update `consumer.sql` with your actual Serper API key.

This script:
- Creates database and schema for secrets
- Creates the secret with Serper API key
- Grants reference usage to the application package
- **Approves External Access Integration for Serper API** (CRITICAL!)
- Starts the application

**IMPORTANT**: The External Access Integration approval (Step 3 in consumer.sql) is REQUIRED for the app to access external APIs like Serper. Without this, you'll get DNS resolution errors.

See [docs/EXTERNAL_ACCESS_SETUP.md](../docs/EXTERNAL_ACCESS_SETUP.md) for detailed troubleshooting if Serper API is not working.

## Updates and Maintenance

### Development Workflow (QA Channel)

When you make changes to the application code and want to test:

```bash
# Full deploy (build + push + deploy)
./scripts/deploy.sh

# Skip Docker build/push (only update app files)
./scripts/deploy.sh --skip-build --skip-push
```

This will:
- Build and push Docker images (unless skipped)
- Upload application files to Snowflake stage
- Create a new patch for the version
- Update the **QA** release channel directive
- Upgrade the test application instance
- Restart the service

### Production Release (DEFAULT Channel)

After testing in QA, release to the marketplace:

```bash
./scripts/release.sh
```

This will:
- **Auto-detect** the version/patch currently in the QA channel
- Promote that exact version/patch to the DEFAULT channel
- Make the new version available to marketplace consumers

You can also specify a specific version/patch manually:

```bash
# Release specific version and patch
./scripts/release.sh --version v1 --patch 5

# Release to ALPHA channel instead of DEFAULT
./scripts/release.sh --channel ALPHA

# Use a different source channel
./scripts/release.sh --from ALPHA --channel DEFAULT
```

### Complete Workflow

```
┌─────────────────────────────────────────────────────────────┐
│  1. DEVELOPMENT                                             │
│     ./scripts/deploy.sh --skip-build --skip-push            │
│     → Creates patch, updates QA channel, upgrades test app  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  2. TEST                                                    │
│     Verify changes in SPCS_APP_INSTANCE_TEST                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  3. PRODUCTION                                              │
│     ./scripts/release.sh                                    │
│     → Reads QA version/patch, promotes to DEFAULT channel   │
└─────────────────────────────────────────────────────────────┘
```

### Release Channels

| Channel | Purpose | Script |
|---------|---------|--------|
| **QA** | Internal testing, not reviewed by Snowflake | `deploy.sh` (automatic) |
| **DEFAULT** | Production, marketplace listing | `release.sh` (promotes from QA) |
| **ALPHA** | For external testing | `release.sh --channel ALPHA` |

### Restarting the Service

If you need to restart the service without deploying:

```bash
./scripts/restart.sh
```

### Recreating Test Application

If you need to recreate the test application:

```bash
./scripts/recreate-app-qa.sh
```

## Available Scripts

| Script | Purpose |
|--------|---------|
| `provider-setup.sh` | **Initial setup** - Creates application package (Provider) |
| `deploy.sh` | Builds and deploys to QA channel (development) |
| `release.sh` | Updates DEFAULT channel (production/marketplace) |
| `create-application.sh` | **Initial setup** - Creates application instance (Consumer) |
| `recreate-app-qa.sh` | Recreates test app using QA release channel |
| `restart.sh` | Restarts the SPCS service |
| `sql/consumer.sql` | **Initial setup** - Consumer secrets and permissions setup |
| `sql/local_setup.sql` | Local development database setup |
| `sql/grant_cortex_permissions.sql` | Grant Cortex AI permissions |

## Configuration

Configuration is managed through environment variables. Copy `.env.example` to `.env` and customize:

```bash
cp .env.example .env
```

Key configuration variables:
- `SNOW_CONNECTION`: Snowflake connection name
- `APP_PROVIDER_ROLE`: Provider role name
- `APP_CONSUMER_ROLE`: Consumer role name
- `APP_PACKAGE_NAME`: Application package name
- `APP_INSTANCE_NAME`: Application instance name
- `APP_VERSION`: Application version
- `COMPUTE_POOL`: SPCS compute pool name

## Monitoring

Check service status:
```bash
snow sql -q "USE ROLE nac_test; CALL spcs_app_instance_test.app_public.get_service_status();" --connection mkt_blendx_demo
```

Get application URL:
```bash
snow sql -q "USE ROLE nac_test; CALL spcs_app_instance_test.app_public.app_url();" --connection mkt_blendx_demo
```

View service logs:
```bash
snow sql -q "USE ROLE nac_test; CALL spcs_app_instance_test.app_public.get_service_logs('eap-backend', 200);" --connection mkt_blendx_demo
```
