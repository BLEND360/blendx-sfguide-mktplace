# Deployment Scripts

This directory contains scripts for deploying and managing the Snowflake Native App.

## Quick Start

### 1. Setup Configuration

Copy the example environment file and customize it for your environment:

```bash
cd scripts
cp .env.example .env
# Edit .env with your specific values
```

Run external_integration.sql 

### 2. Run Deployment

```bash
./scripts/deploy.sh
```

### Command Line Options

#### `--dry-run`
Show what would be done without making any changes:

```bash
./scripts/deploy.sh --dry-run
```

#### `--skip-build`
Skip Docker image building (use existing images):

```bash
./scripts/deploy.sh --skip-build
```

#### `--skip-push`
Skip Docker image push to registry (useful for testing configuration):

```bash
./scripts/deploy.sh --skip-push
```

#### `--help`
Show help message:

```bash
./scripts/deploy.sh --help
```

### Combining Options

Options can be combined:

```bash
# Test deployment without building or pushing images
./scripts/deploy.sh --dry-run --skip-build --skip-push

# Deploy using existing images without rebuilding
./scripts/deploy.sh --skip-build
```

## Deployment Process

The `deploy.sh` script performs the following steps:

1. **Build Docker Images** - Builds backend, frontend, and router images
2. **Login to Registry** - Authenticates with Snowflake Docker registry
3. **Push Images** - Tags and pushes images to Snowflake registry
4. **Upload Files** - Uploads application files to Snowflake stage
5. **Remove Old Version** - Removes previous version from release channel
6. **Drop Old Version** - Deregisters the old version
7. **Register New Version** - Registers the new version with Snowflake
8. **Upgrade Application** - Upgrades the application instance
9. **Restart Service** - Stops and starts the service

## Pre-requisites

Before running the deployment script, ensure you have:

### Required Tools

- **Docker** - For building and pushing container images
- **Snowflake CLI** (`snow`) - For interacting with Snowflake

Verify installation:

```bash
docker --version
snow --version
```

### Snowflake Setup

1. **Connection configured** - Create a Snowflake CLI connection:
   ```bash
   snow connection add
   ```

2. **Roles and permissions** - Ensure you have:
   - A role with permissions to manage application packages (e.g., `naspcs_role`)
   - A role for installing/using the application (e.g., `nac_test`)

3. **Resources created** - The following must exist:
   - Database and schema for the application package
   - Image repository for Docker images
   - Compute pool for running services
   - Warehouse for queries

## Useful Commands

After deployment, use these commands to manage your application:

### View Service Logs

```bash
snow sql -q "USE ROLE nac_test; CALL spcs_app_instance_test.app_public.get_service_logs('eap-backend', 200);" --connection mkt_blendx_demo
```

### Check Service Status

```bash
snow sql -q "USE ROLE nac_test; CALL spcs_app_instance_test.app_public.get_service_status();" --connection mkt_blendx_demo
```

### Get Application URL

```bash
snow sql -q "USE ROLE nac_test; CALL spcs_app_instance_test.app_public.app_url();" --connection mkt_blendx_demo
```

### Stop Service

```bash
snow sql -q "USE ROLE nac_test; CALL spcs_app_instance_test.app_public.stop_app();" --connection mkt_blendx_demo
```

### Start Service

```bash
snow sql -q "USE ROLE nac_test; CALL spcs_app_instance_test.app_public.start_app('POOL_NAC', 'WH_NAC');" --connection mkt_blendx_demo
```

## Troubleshooting

### Connection Issues

If the script fails to connect to Snowflake:

1. Verify your connection:
   ```bash
   snow connection test --connection mkt_blendx_demo
   ```

2. Check your credentials are up to date
3. Ensure you have network access to Snowflake

### Docker Build Failures

If Docker builds fail:

1. Check Docker is running: `docker ps`
2. Verify you have enough disk space
3. Check the Dockerfiles in `backend/`, `frontend/`, and `router/` directories

### Registry Push Failures

If pushing to the Snowflake registry fails:

1. Ensure you're logged in: `snow spcs image-registry login --connection mkt_blendx_demo`
2. Verify the registry URL in your `.env` file
3. Check you have permissions to push to the repository

### Service Start Failures

If the service fails to start:

1. Check service logs:
   ```bash
   snow sql -q "USE ROLE nac_test; CALL spcs_app_instance_test.app_public.get_service_logs('eap-backend', 500);" --connection mkt_blendx_demo
   ```

2. Verify the compute pool is running:
   ```bash
   snow sql -q "SHOW COMPUTE POOLS;" --connection mkt_blendx_demo
   ```

3. Check that the warehouse exists and is accessible

## Environment-Specific Configurations

### Development

For local development, you might want to:

```bash
# Use a dev-specific .env
cp .env.example .env.dev
# Edit .env.dev with dev values

# Deploy using dev config
export $(cat .env.dev | xargs) && ./scripts/deploy.sh
```

### Production

For production deployments:

1. Use a separate `.env.prod` with production values
2. Use version tags instead of `v1` (e.g., `v1.0.0`)
3. Consider using CI/CD pipelines instead of manual deployment

## CI/CD Integration

To use this script in CI/CD pipelines:

### GitHub Actions Example

```yaml
- name: Deploy to Snowflake
  env:
    SNOW_CONNECTION: ${{ secrets.SNOW_CONNECTION }}
    SNOWFLAKE_REGISTRY: ${{ secrets.SNOWFLAKE_REGISTRY }}
  run: |
    ./scripts/deploy.sh --skip-push  # If images are built separately
```

### Environment Variables

All configuration can be set via environment variables instead of using a `.env` file, making it suitable for CI/CD:

```bash
export SNOW_CONNECTION=mkt_blendx_demo
export APP_VERSION=v1.2.3
./scripts/deploy.sh
```

## Additional Scripts

### Lab_Script.sql

Contains SQL commands for initial setup and testing.

### Docker_Commands.txt

Contains reference Docker commands for manual operations.

## Getting Help

- Run `./scripts/deploy.sh --help` for usage information
- Check the main project README for architecture overview
- Review Snowflake Native Apps documentation at https://docs.snowflake.com/en/developer-guide/native-apps/native-apps-about
