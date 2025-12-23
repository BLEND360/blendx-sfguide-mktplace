# BlendX Application Setup Guide

This guide explains how to set up and deploy the BlendX Native Application to Snowflake.

## Prerequisites

- Snowflake account with ACCOUNTADMIN access
- Snowflake CLI (`snow`) installed and configured
- GitHub repository with Actions enabled

## Setup Files

| File | Purpose |
|------|---------|
| `config.sh` | Shared configuration (variables, helper functions) |
| `provider-setup.sh` | Creates Snowflake infrastructure and CI/CD user |
| `create-application.sh` | Creates application instances after first deploy |

## Quick Start

```bash
# 1. Generate RSA keys
mkdir -p keys/pipeline
openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out keys/pipeline/snowflake_key.p8 -nocrypt
openssl rsa -in keys/pipeline/snowflake_key.p8 -pubout -out keys/pipeline/snowflake_key.pub

# 2. (Optional) Customize configuration - edit config.sh or create .env

# 3. Run provider setup
./setup/provider-setup.sh

# 4. Configure GitHub secrets/variables (values shown by script)

# 5. Run "Setup Package" workflow in GitHub Actions

# 6. Create application instances
./setup/create-application.sh --all-envs
```

## Configuration

All configuration is centralized in `config.sh`. You can customize values by:

1. **Editing `config.sh` directly**
2. **Creating a `.env` file** in the setup directory
3. **Setting environment variables** before running scripts

### Configuration Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SNOW_CONNECTION` | `mkt_blendx_demo` | Snowflake CLI connection name |
| `CICD_USER` | `MK_BLENDX_DEPLOY_USER` | CI/CD user name |
| `CICD_ROLE` | `MK_BLENDX_DEPLOY_ROLE` | CI/CD role name |
| `DATABASE_NAME` | `BLENDX_APP_DB` | Database for app artifacts |
| `SCHEMA_NAME` | `BLENDX_SCHEMA` | Schema for app artifacts |
| `WAREHOUSE_NAME` | `BLENDX_APP_WH` | Warehouse name |
| `APP_PACKAGE_NAME` | `MK_BLENDX_APP_PKG` | Application package name |
| `APP_CONSUMER_ROLE` | `BLENDX_APP_ROLE` | Role for app consumers |
| `APP_INSTANCE_BASE` | `BLENDX_APP_INSTANCE` | Application instance base name |
| `COMPUTE_POOL_NAME` | `BLENDX_APP_COMPUTE_POOL` | Compute pool name |

## Step-by-Step Setup

### Step 1: Generate RSA Keys

```bash
mkdir -p keys/pipeline
openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out keys/pipeline/snowflake_key.p8 -nocrypt
openssl rsa -in keys/pipeline/snowflake_key.p8 -pubout -out keys/pipeline/snowflake_key.pub
```

> **Important**: Keep `snowflake_key.p8` secure. Never commit it to the repository.

### Step 2: Run Provider Setup

```bash
./setup/provider-setup.sh
```

This creates:
- Database, schema, stage, and image repository
- CI/CD user with JWT authentication
- CI/CD role with necessary permissions
- Consumer role for app installation

At the end, it shows all GitHub secrets and variables you need to configure.

### Step 3: Configure GitHub

Copy the values shown by the script to **Settings > Secrets and variables > Actions**:

**Secrets:**
- `SNOWFLAKE_ACCOUNT`
- `SNOWFLAKE_HOST`
- `SNOWFLAKE_PRIVATE_KEY_RAW`

**Variables:**
- `SNOWFLAKE_CONNECTION`
- `SNOWFLAKE_DEPLOY_USER`
- `SNOWFLAKE_DEPLOY_ROLE`
- `SNOWFLAKE_WAREHOUSE`
- `SNOWFLAKE_DATABASE`
- `SNOWFLAKE_SCHEMA`
- `SNOWFLAKE_REPO`
- `SNOWFLAKE_APP_PACKAGE`
- `SNOWFLAKE_APP_INSTANCE`
- `SNOWFLAKE_COMPUTE_POOL`
- `SNOWFLAKE_ROLE`

### Step 4: Run Setup Package Workflow

In GitHub Actions, manually run the **"Setup Package"** workflow. This:
- Builds and pushes Docker images
- Creates the application package
- Registers the first version

### Step 5: Create Application Instances

After the workflow completes:

```bash
./setup/create-application.sh --all-envs
```

This creates:
- `BLENDX_APP_INSTANCE_QA` - for QA testing
- `BLENDX_APP_INSTANCE_STABLE` - for stable/pre-production

Options:
```bash
./setup/create-application.sh              # Creates default instance
./setup/create-application.sh --env qa     # Creates only _QA
./setup/create-application.sh --env stable # Creates only _STABLE
./setup/create-application.sh --all-envs   # Creates both _QA and _STABLE
```

### Step 6: Configure Application (UI)

After the application is created, go to Snowsight:

1. Navigate to **Data Products** > **Apps** > **BLENDX_APP_INSTANCE_QA**
2. Click on the application
3. Go to the **Security** tab
4. Configure any required references (e.g., Serper API key secret)

### Step 7: Start Application

Start the application manually:

```sql
USE ROLE BLENDX_APP_ROLE;
CALL BLENDX_APP_INSTANCE_QA.app_public.start_app('BLENDX_APP_COMPUTE_POOL');
```

### Step 8: Get Application URL

Once the service is running, get the URL:

```sql
USE ROLE BLENDX_APP_ROLE;
CALL BLENDX_APP_INSTANCE_QA.app_public.app_url();
```

## Useful Commands

```sql
-- Check service status
CALL BLENDX_APP_INSTANCE_QA.app_public.get_service_status();

-- View service logs
CALL BLENDX_APP_INSTANCE_QA.app_public.get_service_logs('frontend', 100);
CALL BLENDX_APP_INSTANCE_QA.app_public.get_service_logs('backend', 100);

-- Stop the service
CALL BLENDX_APP_INSTANCE_QA.app_public.stop_app();

-- Check application versions
USE ROLE MK_BLENDX_DEPLOY_ROLE;
SHOW VERSIONS IN APPLICATION PACKAGE MK_BLENDX_APP_PKG;

-- Check release channels
SHOW RELEASE CHANNELS IN APPLICATION PACKAGE MK_BLENDX_APP_PKG;
```

## Subsequent Updates

After the initial setup, the pipeline will automatically:
1. Build new images
2. Add patches to the application package
3. Update the QA release channel
4. Upgrade the application instance (if it exists)
5. Restart the service

**No manual intervention required for updates.**

## Troubleshooting

### Application creation fails with privilege error
Make sure the pipeline has run at least once to deploy the latest setup.sql that creates the External Access Integration in `start_app()` instead of during setup.

### Service won't start
Check the service logs:
```sql
CALL BLENDX_APP_INSTANCE_QA.app_public.get_service_logs('backend', 100);
```

### Upgrade fails
Verify the version and patch exist:
```sql
SHOW VERSIONS IN APPLICATION PACKAGE MK_BLENDX_APP_PKG;
```
