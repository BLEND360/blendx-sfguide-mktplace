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

### Updating Application Code

When you make changes to the application code (backend, frontend, router):

```bash
./scripts/deploy.sh
```

This will:
- Rebuild and push Docker images
- Update the application version
- Upgrade the existing application instance
- Restart the service

### Restarting the Service

If you need to restart the service without deploying:

```bash
./scripts/restart.sh
```

### Releasing a New Version

To create and publish a new version:

```bash
./scripts/release.sh
```

## Available Scripts

| Script | Purpose |
|--------|---------|
| `provider-setup.sh` | **Initial setup** - Creates application package (Provider) |
| `deploy.sh` | Builds and deploys application code |
| `create-application.sh` | **Initial setup** - Creates application instance (Consumer) |
| `restart.sh` | Restarts the SPCS service |
| `release.sh` | Creates and publishes a new version |
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

## Troubleshooting

### Application instance doesn't exist
Make sure you've run `create-application.sh` first.

### Secret not found
Ensure `consumer.sql` has been executed with the correct API key.

### Service not starting
Check the compute pool is running and accessible:
```bash
snow sql -q "SHOW COMPUTE POOLS;" --connection mkt_blendx_demo
```

### Permission errors
Verify all grants in `consumer.sql` were executed successfully. 