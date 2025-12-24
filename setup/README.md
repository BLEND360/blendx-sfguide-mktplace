# BlendX Application Setup

This folder contains the scripts for initial Snowflake setup.

## Scripts

| File | Purpose |
|------|---------|
| `config.sh` | Shared configuration (variables, helper functions) |
| `provider-setup.sh` | Creates Snowflake infrastructure and CI/CD user |
| `create-application.sh` | Creates application instances (QA, STABLE) |

## Quick Start

```bash
# 1. Generate RSA keys
mkdir -p keys/pipeline
openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out keys/pipeline/snowflake_key.p8 -nocrypt
openssl rsa -in keys/pipeline/snowflake_key.p8 -pubout -out keys/pipeline/snowflake_key.pub

# 2. Run provider setup
./setup/provider-setup.sh

# 3. Configure GitHub secrets/variables (values shown by script)

# 4. Run "Setup Package" workflow in GitHub Actions

# 5. Create application instances
./setup/create-application.sh --all-envs

# 6. Activate and configure the app in Snowflake UI

# 7. Start the application
CALL BLENDX_APP_INSTANCE_QA.APP_PUBLIC.START_APP('QA');
```

## Full Documentation

For complete setup instructions, configuration details, and CI/CD pipeline information, see:

**[docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md)**

## Useful Commands

```sql
-- Start the application
CALL BLENDX_APP_INSTANCE_QA.APP_PUBLIC.START_APP('QA');

-- Get application URL
CALL BLENDX_APP_INSTANCE_QA.APP_PUBLIC.APP_URL();

-- Check service status
CALL BLENDX_APP_INSTANCE_QA.APP_PUBLIC.GET_SERVICE_STATUS();

-- View service logs
CALL BLENDX_APP_INSTANCE_QA.APP_PUBLIC.GET_SERVICE_LOGS('backend', 100);

-- Stop the service
CALL BLENDX_APP_INSTANCE_QA.APP_PUBLIC.STOP_APP();
```
