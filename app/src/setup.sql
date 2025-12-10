CREATE SCHEMA IF NOT EXISTS config;
CREATE APPLICATION ROLE IF NOT EXISTS app_admin;
CREATE APPLICATION ROLE IF NOT EXISTS app_user;
CREATE SCHEMA IF NOT EXISTS app_public;
GRANT USAGE ON SCHEMA config TO APPLICATION ROLE app_admin;

GRANT USAGE ON SCHEMA app_public TO APPLICATION ROLE app_admin;
GRANT USAGE ON SCHEMA app_public TO APPLICATION ROLE app_user;
CREATE OR ALTER VERSIONED SCHEMA v1;
GRANT USAGE ON SCHEMA v1 TO APPLICATION ROLE app_admin;

-- Create network rule for Serper API access (required for EAI)
CREATE OR REPLACE NETWORK RULE app_public.serper_network_rule
    TYPE = HOST_PORT
    VALUE_LIST = ('google.serper.dev')
    MODE = EGRESS;

-- Create external access integration for Serper API
CREATE OR REPLACE EXTERNAL ACCESS INTEGRATION serper_eai
    ALLOWED_NETWORK_RULES = (app_public.serper_network_rule)
    ENABLED = TRUE;

-- Define app specification for external access (required for Marketplace)
ALTER APPLICATION SET SPECIFICATION serper_api_spec
    TYPE = EXTERNAL_ACCESS
    LABEL = 'Serper Web Search API'
    DESCRIPTION = 'Allows the application to connect to google.serper.dev for web search functionality'
    HOST_PORTS = ('google.serper.dev');

-- Create schema for application data
CREATE SCHEMA IF NOT EXISTS app_data;
GRANT USAGE ON SCHEMA app_data TO APPLICATION ROLE app_admin;
GRANT USAGE ON SCHEMA app_data TO APPLICATION ROLE app_user;

-- Create table to store Crew execution results
CREATE OR REPLACE TABLE app_data.crew_execution_results (
    id VARCHAR(36) PRIMARY KEY,
    execution_timestamp TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    crew_name VARCHAR(255),
    raw_output VARIANT,
    result_text TEXT,
    status VARCHAR(50),
    error_message TEXT,
    metadata VARIANT
);

-- Grant permissions to read results
GRANT SELECT ON TABLE app_data.crew_execution_results TO APPLICATION ROLE app_user;
GRANT SELECT, INSERT, UPDATE ON TABLE app_data.crew_execution_results TO APPLICATION ROLE app_admin;

-- Create table to store Crew executions (used by backend ORM)
CREATE OR REPLACE TABLE app_data.crew_executions (
    id VARCHAR(36) PRIMARY KEY,
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    name VARCHAR(255),
    input TEXT,
    output TEXT,
    context VARIANT,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    finished_at TIMESTAMP_NTZ,
    execution_group_id VARCHAR(36),
    flow_execution_id VARCHAR(36)
);

-- Grant permissions for crew_executions table
GRANT SELECT ON TABLE app_data.crew_executions TO APPLICATION ROLE app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE app_data.crew_executions TO APPLICATION ROLE app_admin;

-- Create table to store Workflows (execution groups and flows from NL generator)
CREATE OR REPLACE TABLE app_data.workflows (
    workflow_id VARCHAR(255) NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    type VARCHAR(50) NOT NULL,
    mermaid TEXT,
    title VARCHAR(255),
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    rationale TEXT,
    yaml_text TEXT NOT NULL,
    chat_id VARCHAR(255),
    message_id VARCHAR(255),
    user_id VARCHAR(255),
    model VARCHAR(100),
    stable BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (workflow_id, version)
);

-- Grant permissions for workflows table
GRANT SELECT ON TABLE app_data.workflows TO APPLICATION ROLE app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE app_data.workflows TO APPLICATION ROLE app_admin;

CREATE OR REPLACE PROCEDURE app_public.start_app(poolname VARCHAR)
    RETURNS string
    LANGUAGE sql
    AS $$
BEGIN
        LET app_warehouse VARCHAR DEFAULT 'APP_WH';

        -- First, create the application warehouse
        CREATE WAREHOUSE IF NOT EXISTS IDENTIFIER(:app_warehouse)
            WAREHOUSE_SIZE = 'X-SMALL'
            AUTO_SUSPEND = 60
            AUTO_RESUME = TRUE
            INITIALLY_SUSPENDED = TRUE;

        -- Create compute pool if it doesn't exist
        EXECUTE IMMEDIATE 'CREATE COMPUTE POOL IF NOT EXISTS ' || poolname ||
            ' MIN_NODES = 1 MAX_NODES = 3 INSTANCE_FAMILY = CPU_X64_M AUTO_RESUME = TRUE AUTO_SUSPEND_SECS = 300';

        -- Create the service with the app's external access integration (EAI created at setup time)
        EXECUTE IMMEDIATE 'CREATE SERVICE app_public.st_spcs IN COMPUTE POOL ' || poolname ||
            ' FROM SPECIFICATION_FILE=''/fullstack.yaml'' QUERY_WAREHOUSE=' || app_warehouse ||
            ' EXTERNAL_ACCESS_INTEGRATIONS = (serper_eai)';

        GRANT USAGE ON SERVICE app_public.st_spcs TO APPLICATION ROLE app_user;
        GRANT SERVICE ROLE app_public.st_spcs!ALL_ENDPOINTS_USAGE TO APPLICATION ROLE app_user;

        RETURN 'Service started with warehouse ' || app_warehouse || '. Check status, and when ready, get URL';
END;
$$;

GRANT USAGE ON PROCEDURE app_public.start_app(VARCHAR) TO APPLICATION ROLE app_admin;

CREATE OR REPLACE PROCEDURE app_public.stop_app()
    RETURNS string
    LANGUAGE sql
    AS
$$
BEGIN
    DROP SERVICE IF EXISTS app_public.st_spcs;
END
$$;
GRANT USAGE ON PROCEDURE app_public.stop_app() TO APPLICATION ROLE app_admin;

CREATE OR REPLACE PROCEDURE app_public.app_url()
    RETURNS string
    LANGUAGE sql
    AS
$$
BEGIN
    LET ingress_url VARCHAR;
    SHOW ENDPOINTS IN SERVICE app_public.st_spcs;
    SELECT "ingress_url" INTO :ingress_url FROM TABLE (RESULT_SCAN (LAST_QUERY_ID())) LIMIT 1;
    RETURN ingress_url;
END
$$;
GRANT USAGE ON PROCEDURE app_public.app_url() TO APPLICATION ROLE app_admin;
GRANT USAGE ON PROCEDURE app_public.app_url() TO APPLICATION ROLE app_user;

CREATE OR REPLACE PROCEDURE app_public.get_service_logs(container_name VARCHAR, num_lines NUMBER)
    RETURNS STRING
    LANGUAGE sql
    AS
$$
BEGIN
    RETURN SYSTEM$GET_SERVICE_LOGS('app_public.st_spcs', 0, :container_name, :num_lines);
END
$$;
GRANT USAGE ON PROCEDURE app_public.get_service_logs(VARCHAR, NUMBER) TO APPLICATION ROLE app_admin;

CREATE OR REPLACE PROCEDURE app_public.get_service_status()
    RETURNS STRING
    LANGUAGE sql
    AS
$$
BEGIN
    RETURN SYSTEM$GET_SERVICE_STATUS('app_public.st_spcs');
END
$$;
GRANT USAGE ON PROCEDURE app_public.get_service_status() TO APPLICATION ROLE app_admin;

-- Procedure to get the last crew execution result
CREATE OR REPLACE PROCEDURE app_public.get_last_crew_execution()
    RETURNS TABLE (
        id VARCHAR,
        execution_timestamp TIMESTAMP_NTZ,
        updated_at TIMESTAMP_NTZ,
        crew_name VARCHAR,
        raw_output VARIANT,
        result_text TEXT,
        status VARCHAR,
        error_message TEXT,
        metadata VARIANT
    )
    LANGUAGE sql
    AS
$$
BEGIN
    LET result_cursor CURSOR FOR
        SELECT
            id,
            execution_timestamp,
            updated_at,
            crew_name,
            raw_output,
            result_text,
            status,
            error_message,
            metadata
        FROM app_data.crew_execution_results
        ORDER BY execution_timestamp DESC
        LIMIT 1;
    OPEN result_cursor;
    RETURN TABLE(result_cursor);
END;
$$;
GRANT USAGE ON PROCEDURE app_public.get_last_crew_execution() TO APPLICATION ROLE app_admin;
GRANT USAGE ON PROCEDURE app_public.get_last_crew_execution() TO APPLICATION ROLE app_user;

-- Procedure to get recent crew executions (last N)
CREATE OR REPLACE PROCEDURE app_public.get_recent_crew_executions(num_results NUMBER)
    RETURNS TABLE (
        id VARCHAR,
        execution_timestamp TIMESTAMP_NTZ,
        updated_at TIMESTAMP_NTZ,
        crew_name VARCHAR,
        raw_output VARIANT,
        result_text TEXT,
        status VARCHAR,
        error_message TEXT,
        metadata VARIANT
    )
    LANGUAGE sql
    AS
$$
BEGIN
    LET result_cursor CURSOR FOR
        SELECT
            id,
            execution_timestamp,
            updated_at,
            crew_name,
            raw_output,
            result_text,
            status,
            error_message,
            metadata
        FROM app_data.crew_execution_results
        ORDER BY execution_timestamp DESC
        LIMIT :num_results;
    OPEN result_cursor;
    RETURN TABLE(result_cursor);
END;
$$;
GRANT USAGE ON PROCEDURE app_public.get_recent_crew_executions(NUMBER) TO APPLICATION ROLE app_admin;
GRANT USAGE ON PROCEDURE app_public.get_recent_crew_executions(NUMBER) TO APPLICATION ROLE app_user;

-- Procedure to count total crew executions
CREATE OR REPLACE PROCEDURE app_public.count_crew_executions()
    RETURNS NUMBER
    LANGUAGE sql
    AS
$$
BEGIN
    LET total_count NUMBER;
    SELECT COUNT(*) INTO :total_count FROM app_data.crew_execution_results;
    RETURN total_count;
END;
$$;
GRANT USAGE ON PROCEDURE app_public.count_crew_executions() TO APPLICATION ROLE app_admin;
GRANT USAGE ON PROCEDURE app_public.count_crew_executions() TO APPLICATION ROLE app_user;


CREATE OR REPLACE PROCEDURE config.get_config_for_ref(reference_name STRING)
  RETURNS VARCHAR
  LANGUAGE SQL
AS
$$
BEGIN
    CASE (UPPER(reference_name))
        WHEN 'SERPER_API_KEY' THEN
            RETURN '{"type": "CONFIGURATION", "payload": {"type": "GENERIC_STRING"}}';
        ELSE
            RETURN '{"type": "ERROR", "payload": {"message": "Unknown reference"}}';
    END CASE;
END;
$$;
GRANT USAGE ON PROCEDURE config.get_config_for_ref(STRING) TO APPLICATION ROLE app_admin;




CREATE OR REPLACE PROCEDURE CONFIG.REGISTER_SINGLE_REFERENCE(
  ref_name STRING, operation STRING, ref_or_alias STRING)
  RETURNS STRING
  LANGUAGE SQL
  AS $$
    DECLARE
      result STRING;
    BEGIN
      CASE (UPPER(operation))
        WHEN 'ADD' THEN
          result := SYSTEM$SET_REFERENCE(:ref_name, :ref_or_alias);
        WHEN 'REMOVE' THEN
          result := SYSTEM$REMOVE_REFERENCE(:ref_name);
        WHEN 'CLEAR' THEN
          result := SYSTEM$REMOVE_REFERENCE(:ref_name);
      ELSE
        RETURN 'unknown operation: ' || UPPER(operation);
      END CASE;
      RETURN 'Reference ' || :ref_name || ' ' || UPPER(:operation) || ' successful: ' || result;
    END;
  $$;

GRANT USAGE
  ON PROCEDURE CONFIG.REGISTER_SINGLE_REFERENCE(STRING, STRING, STRING)
  TO APPLICATION ROLE APP_ADMIN;