# BlendX Backend - CrewAI with Snowflake Cortex

Backend API for running CrewAI agents with Snowflake Cortex LLMs.

## Prerequisites

### Snowflake Cortex Permissions

For the application to access Snowflake Cortex, you need to grant the following permissions:

```sql
-- Grant Cortex user role to the application role
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE naspcs_role;

-- Grant Cortex user role to the application
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO APPLICATION spcs_app_instance_test;

-- Grant imported privileges on Snowflake database to the application
-- This is required for REST API access to Cortex
GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO APPLICATION spcs_app_instance_test;
```

**Note:** Replace `naspcs_role` and `spcs_app_instance_test` with your actual role and application names.

These grants are required because:
- `CORTEX_USER` role provides access to Snowflake Cortex functions (SQL access)
- `IMPORTED PRIVILEGES ON SNOWFLAKE DB` provides access to Cortex REST API endpoints

## Architecture

### LLM Handler (`lite_llm_handler.py`)

The application uses different Cortex endpoints depending on the environment:

- **SPCS (OAuth)**: Uses native Cortex endpoint `/api/v2/cortex/inference:complete`
- **Local (JWT)**: Uses OpenAI-compatible endpoint `/api/v2/cortex/v1`

### API Endpoints

- `GET /health` - Health check with OAuth token status
- `GET /test-cortex` - Test Cortex via SQL (`SNOWFLAKE.CORTEX.COMPLETE`)
- `GET /test-litellm` - Test LiteLLM/REST API connection
- `POST /crew/start` - Start crew execution (async)
- `GET /crew/status/{execution_id}` - Get crew execution status
- `GET /crew/executions` - List recent executions

## Local Development

1. Create `.env` file with your Snowflake credentials:
```env
SNOWFLAKE_USER=your.user@company.com
SNOWFLAKE_DATABASE=your_database
SNOWFLAKE_SCHEMA=your_schema
SNOWFLAKE_ROLE=your_role
SNOWFLAKE_WAREHOUSE=your_warehouse
SNOWFLAKE_HOST=your-account.snowflakecomputing.com
SNOWFLAKE_ACCOUNT=your-account
SNOWFLAKE_SERVICE_USER=your.user@company.com
SNOWFLAKE_AUTHMETHOD=jwt
SNOWFLAKE_PRIVATE_KEY_PATH=/path/to/keys/rsa_key.p8
ENVIRONMENT=LOCAL
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
cd backend/src
python fastapi_app.py
```

## Troubleshooting

### "Not authorized for this endpoint" error

This error occurs when the application doesn't have proper Cortex permissions. Ensure:

1. The application has `CORTEX_USER` role granted
2. The application has `IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE`
3. The manifest includes `IMPORTED PRIVILEGES ON SNOWFLAKE DB` privilege

### Testing connectivity

Use the diagnostic endpoints to test each layer:

1. **Test SQL access**: `GET /test-cortex` - Tests `SNOWFLAKE.CORTEX.COMPLETE`
2. **Test REST API**: `GET /test-litellm` - Tests LiteLLM handler and Cortex REST endpoint
3. **Test full crew**: `POST /crew/start` - Tests complete CrewAI integration
