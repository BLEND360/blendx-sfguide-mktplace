CREATE SCHEMA IF NOT EXISTS config;
CREATE APPLICATION ROLE IF NOT EXISTS app_admin;
CREATE APPLICATION ROLE IF NOT EXISTS app_user;
CREATE SCHEMA IF NOT EXISTS app_public;
GRANT USAGE ON SCHEMA config TO APPLICATION ROLE app_admin;

GRANT USAGE ON SCHEMA app_public TO APPLICATION ROLE app_admin;
GRANT USAGE ON SCHEMA app_public TO APPLICATION ROLE app_user;
CREATE OR ALTER VERSIONED SCHEMA v1;
GRANT USAGE ON SCHEMA v1 TO APPLICATION ROLE app_admin;

-- Create schema for application data
CREATE SCHEMA IF NOT EXISTS app_data;
GRANT USAGE ON SCHEMA app_data TO APPLICATION ROLE app_admin;
GRANT USAGE ON SCHEMA app_data TO APPLICATION ROLE app_user;

-- Note: External Access Integration must be created by the consumer
-- and referenced to this application. See deployment scripts.

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

CREATE OR REPLACE PROCEDURE app_public.start_app(poolname VARCHAR, whname VARCHAR)
    RETURNS string
    LANGUAGE sql
    AS $$
BEGIN
        -- First, create compute pool if it doesn't exist
        EXECUTE IMMEDIATE 'CREATE COMPUTE POOL IF NOT EXISTS ' || poolname || '
            MIN_NODES = 1
            MAX_NODES = 3
            INSTANCE_FAMILY = CPU_X64_M
            AUTO_RESUME = TRUE';

        -- Then create the service with external access integration from consumer reference
        EXECUTE IMMEDIATE 'CREATE SERVICE IF NOT EXISTS app_public.st_spcs
            IN COMPUTE POOL ' || poolname || '
            FROM SPECIFICATION_FILE=''/fullstack.yaml''
            QUERY_WAREHOUSE=' || whname || '
            EXTERNAL_ACCESS_INTEGRATIONS = (REFERENCE(''serper_access_integration''))';

        GRANT USAGE ON SERVICE app_public.st_spcs TO APPLICATION ROLE app_user;
        GRANT SERVICE ROLE app_public.st_spcs!ALL_ENDPOINTS_USAGE TO APPLICATION ROLE app_user;

        RETURN 'Service started. Check status, and when ready, get URL';
END;
$$;
GRANT USAGE ON PROCEDURE app_public.start_app(VARCHAR, VARCHAR) TO APPLICATION ROLE app_admin;

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
DECLARE
    ingress_url VARCHAR;
BEGIN
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
DECLARE
    total_count NUMBER;
BEGIN
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


create or replace procedure config.get_configuration(ref_name string)
returns string
language sql
as $$
begin
    CASE (UPPER(ref_name))
        WHEN 'SERPER_ACCESS_INTEGRATION' THEN
            RETURN '{
                "type": "CONFIGURATION",
                "payload": {
                    "host_ports": ["serper.dev", "google.serper.dev"],
                    "allowed_secrets": "ALL"
                }
            }';
        ELSE
            RETURN '{
                "type": "ERROR",
                "payload": {
                    "message": "The reference is not available for configuration"
                }
            }';
    END CASE;
end;
$$;

GRANT USAGE ON PROCEDURE CONFIG.get_configuration(STRING)
  TO APPLICATION ROLE app_admin;


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