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

When you first open the application, you will be prompted to grant serper external access integration privileges.

Click **Grant** to approve these privileges.

---

### Step 2: Activate the Application

1. Return to the application page in the Snowflake UI
2. Click **Activate** to start the application
3. Wait for the service to initialize (this may take a few minutes)


### Step 3: Configure Serper API Secret (Required for External Tools)

The application uses Serper API for web search functionality. You need to create a secret with your API key.

**Note**: The application automatically creates the External Access Integration - you only need to provide the API key secret.

#### 3.1 Create Secret

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

-- Grant reference usage on the secrets database to the application package
GRANT REFERENCE_USAGE ON DATABASE secrets_db
  TO SHARE IN APPLICATION PACKAGE <app_package_name>;
```

---

### Step 4: Configure Application References

In the Snowflake UI, configure the following reference at connections section:

#### Object Access Privileges

- **Serper API Key** → `secrets_db.app_secrets.serper_api_key`

Click on the reference and select the secret you created in the previous step.

**Note**: The application creates its own External Access Integration automatically.

---

### Step 5: Start the Application Service

After activation, start the service by calling:

```sql
CALL <app_name>.app_public.start_app('<pool_name>');
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

## Quick Reference - SQL Commands

```sql
-- Replace placeholders with your actual values:
-- <app_name>: Your application instance name
-- <pool_name>: Your compute pool name
-- <your_role>: Your Snowflake role

-- Start application
CALL <app_name>.app_public.start_app('<pool_name>');

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
