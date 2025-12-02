# BlendX - CrewAI Native Application

A Snowflake Native Application that runs CrewAI workflows using Snowpark Container Services (SPCS), powered by Snowflake Cortex LLMs.

## Features

- Run CrewAI agent workflows directly in Snowflake
- Powered by Snowflake Cortex LLMs (no external API keys required for LLM)
- External tool integration via Serper API for web search capabilities
- Secure secret management through Snowflake references

---

## Consumer Setup Guide

Follow these steps after installing the application from the Snowflake Marketplace.

### Step 1: Grant Account-Level Privileges

When you first open the application, you will be prompted to grant the following privileges:

- **IMPORTED PRIVILEGES ON SNOWFLAKE DB** - Access Snowflake Cortex AI functions
- **CREATE COMPUTE POOL** - Create compute resources for the application
- **BIND SERVICE ENDPOINT** - Expose the application's web interface
- **CREATE WAREHOUSE** - Create a warehouse for query execution
- **EXECUTE MANAGED TASK** - Execute Cortex functions
- **CREATE EXTERNAL ACCESS INTEGRATION** - Enable external API connections (Serper)

Click **Grant** to approve these privileges.

---

### Step 2: Configure Serper API Secret (Required for External Tools)

The application uses Serper API for web search functionality. You need to create a secret with your API key.

#### 2.1 Create Secret Infrastructure

```sql
-- Use your role (replace with your actual role)
USE ROLE <your_role>;

-- Create database and schema for secrets
CREATE DATABASE IF NOT EXISTS secrets_db;
CREATE SCHEMA IF NOT EXISTS secrets_db.app_secrets;

-- Create the secret with your Serper API key
-- Get your API key from https://serper.dev
CREATE SECRET IF NOT EXISTS secrets_db.app_secrets.serper_api_key
  TYPE = GENERIC_STRING
  SECRET_STRING = '<your_serper_api_key>';
```

#### 2.2 Grant Secret Access to Application Package

```sql
-- Grant reference usage on the secrets database to the application package
GRANT REFERENCE_USAGE ON DATABASE secrets_db
  TO SHARE IN APPLICATION PACKAGE <app_package_name>;
```

---

### Step 3: Create External Access Integration for Serper

```sql
-- Create network rule for Serper API
CREATE NETWORK RULE IF NOT EXISTS secrets_db.app_secrets.serper_network_rule
  TYPE = HOST_PORT
  VALUE_LIST = ('google.serper.dev')
  MODE = EGRESS;

-- Create external access integration
CREATE OR REPLACE EXTERNAL ACCESS INTEGRATION serper_access_integration
  ALLOWED_NETWORK_RULES = (secrets_db.app_secrets.serper_network_rule)
  ALLOWED_AUTHENTICATION_SECRETS = (secrets_db.app_secrets.serper_api_key)
  ENABLED = TRUE;

GRANT USAGE ON INTEGRATION serper_access_integration TO ROLE nac_test;

```

---

### Step 4: Configure Application References

In the Snowflake UI, navigate to **Data Products > Apps > [Your App Name]** and configure the following references:

#### Object Access Privileges

- **Serper secret** → `secrets_db.app_secrets.serper_api_key`
- **Serper External Access** → `serper_access_integration`

Click on each reference and select the corresponding object you created in the previous steps.

---

### Step 5: Create Compute Pool and Warehouse

```sql
-- Create compute pool for the application
CREATE COMPUTE POOL IF NOT EXISTS <pool_name>
  MIN_NODES = 1
  MAX_NODES = 3
  INSTANCE_FAMILY = CPU_X64_M
  AUTO_RESUME = TRUE;

-- Grant compute pool to the application
GRANT USAGE ON COMPUTE POOL <pool_name> TO APPLICATION <app_name>;

-- Grant warehouse permissions (use existing or create new)
GRANT USAGE ON WAREHOUSE <warehouse_name> TO APPLICATION <app_name>;
GRANT OPERATE ON WAREHOUSE <warehouse_name> TO APPLICATION <app_name>;
```

---

### Step 6: Activate the Application

1. Return to the application page in the Snowflake UI
2. Click **Activate** to start the application
3. Wait for the service to initialize (this may take a few minutes)

---

### Step 7: Start the Application Service

After activation, start the service by calling:

```sql
CALL <app_name>.app_public.start_app('<pool_name>', '<warehouse_name>');
```

Check the service status:

```sql
CALL <app_name>.app_public.get_service_status();
```

Get the application URL:

```sql
CALL <app_name>.app_public.app_url();
```

---

## Using the Application

Once the application is running, open the URL returned by `app_url()` to access the web interface.

### Available Features

- **TEST CORTEX** - Verify Cortex LLM connectivity
- **TEST LITELLM** - Test LiteLLM integration
- **TEST SECRETS** - Verify secret configuration
- **TEST SERPER** - Test Serper API connectivity
- **RUN TEST CREW** - Execute a basic CrewAI workflow
- **RUN TEST EXTERNAL TOOL** - Execute workflow with Serper web search
- **LIST TEST CREWS** - View execution history of TEST crews

---

## Troubleshooting

### Cortex Test Fails

Ensure you granted `IMPORTED PRIVILEGES ON SNOWFLAKE DB` when prompted. If needed, manually grant:

```sql
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO APPLICATION <app_name>;
GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO APPLICATION <app_name>;
```

### Serper Test Fails

1. Verify your Serper API key is correct
2. Check that the secret reference is configured in the app
3. Ensure the external access integration is granted to the app

### Service Won't Start

Check service logs for errors:

```sql
CALL <app_name>.app_public.get_service_logs('eap-backend', 200);
```

### Stop the Application

```sql
CALL <app_name>.app_public.stop_app();
```

---

## Quick Reference - SQL Commands

```sql
-- Replace placeholders with your actual values:
-- <app_name>: Your application instance name
-- <pool_name>: Your compute pool name
-- <warehouse_name>: Your warehouse name
-- <your_role>: Your Snowflake role

-- Start application
CALL <app_name>.app_public.start_app('<pool_name>', '<warehouse_name>');

-- Get application URL
CALL <app_name>.app_public.app_url();

-- Check service status
CALL <app_name>.app_public.get_service_status();

-- View logs
CALL <app_name>.app_public.get_service_logs('eap-backend', 200);
CALL <app_name>.app_public.get_service_logs('eap-frontend', 200);

-- Stop application
CALL <app_name>.app_public.stop_app();

-- View recent crew executions
CALL <app_name>.app_public.get_recent_crew_executions(10);
```
