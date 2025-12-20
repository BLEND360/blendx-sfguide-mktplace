# BlendX Application Setup Guide

This guide explains how to set up and deploy the BlendX Native Application to Snowflake.

## Prerequisites

- Snowflake account with ACCOUNTADMIN access
- Snowflake CLI (`snow`) installed
- GitHub repository with Actions enabled
- RSA key pair for CI/CD authentication

## Setup Steps

### Step 1: Provider Setup (One-time)

Run the provider setup script as ACCOUNTADMIN to create:
- Database, schema, stage, and image repository
- CI/CD user with JWT authentication
- CI/CD role with necessary permissions
- Application package (optional)

```bash
# Generate RSA keys first (if not already done)
mkdir -p keys/pipeline
openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out keys/pipeline/snowflake_key.p8 -nocrypt
openssl rsa -in keys/pipeline/snowflake_key.p8 -pubout -out keys/pipeline/snowflake_key.pub

# Run provider setup
./setup/provider-setup.sh
```

After running, configure the GitHub secrets as shown in the script output.

### Step 2: Run Pipeline (First Deploy)

Push to the `develop` branch or trigger the workflow manually to:
- Build and push Docker images
- Upload application files to stage
- Create/update application package
- Register version and patches

```bash
git push origin develop
```

Or trigger manually via GitHub Actions.

### Step 3: Create Application Instance (One-time)

After the pipeline has deployed at least one version, run:

```bash
./setup/create-application.sh
```

This script will:
1. Check for available versions in the package
2. Get the latest patch number
3. Create the application instance
4. Grant required account-level permissions (CREATE COMPUTE POOL, BIND SERVICE ENDPOINT, CREATE WAREHOUSE, CREATE EXTERNAL ACCESS INTEGRATION)
5. Optionally start the application service

### Step 4: Configure Application (UI)

After the application is created, go to Snowsight:

1. Navigate to **Data Products** > **Apps** > **BLENDX_APP_INSTANCE**
2. Click on the application
3. Go to the **Security** tab
4. Configure any required references (e.g., Serper API key secret)

### Step 5: Start Application

Run the pipeline again or start the application manually:

```sql
USE ROLE BLENDX_APP_ROLE;
CALL BLENDX_APP_INSTANCE.app_public.start_app('BLENDX_CP');
```
 

### Step 6: Get Application URL

Once the service is running, get the URL:

```sql
USE ROLE BLENDX_APP_ROLE;
CALL BLENDX_APP_INSTANCE.app_public.app_url();
```

## Useful Commands

```sql
-- Check service status
CALL BLENDX_APP_INSTANCE.app_public.get_service_status();

-- View service logs
CALL BLENDX_APP_INSTANCE.app_public.get_service_logs('frontend', 100);
CALL BLENDX_APP_INSTANCE.app_public.get_service_logs('backend', 100);

-- Stop the service
CALL BLENDX_APP_INSTANCE.app_public.stop_app();

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

## Configuration Variables

Both scripts use the same default values. Override via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `SNOW_CONNECTION` | `mkt_blendx_demo` | Snowflake CLI connection name |
| `CICD_USER` | `MK_BLENDX_DEPLOY_USER` | CI/CD user name |
| `CICD_ROLE` | `MK_BLENDX_DEPLOY_ROLE` | CI/CD role name |
| `DATABASE_NAME` | `BLENDX_APP` | Database for app artifacts |
| `SCHEMA_NAME` | `NAPP` | Schema for app artifacts |
| `APP_PACKAGE_NAME` | `MK_BLENDX_APP_PKG` | Application package name |
| `APP_CONSUMER_ROLE` | `BLENDX_APP_ROLE` | Role for app consumers |
| `APP_INSTANCE_NAME` | `BLENDX_APP_INSTANCE` | Application instance name |
| `COMPUTE_POOL_NAME` | `BLENDX_CP` | Compute pool name |

## Troubleshooting

### Application creation fails with privilege error
Make sure the pipeline has run at least once to deploy the latest setup.sql that creates the External Access Integration in `start_app()` instead of during setup.

### Service won't start
Check the service logs:
```sql
CALL BLENDX_APP_INSTANCE.app_public.get_service_logs('backend', 100);
```

### Upgrade fails
Verify the version and patch exist:
```sql
SHOW VERSIONS IN APPLICATION PACKAGE MK_BLENDX_APP_PKG;
```
