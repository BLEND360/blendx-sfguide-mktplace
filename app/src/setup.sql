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


-- Create table to store Crew execution results
CREATE TABLE IF NOT EXISTS app_data.crew_execution_results (
    id VARCHAR(36) PRIMARY KEY,
    execution_timestamp TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
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
        EXECUTE IMMEDIATE 'CREATE SERVICE IF NOT EXISTS app_public.st_spcs
            IN COMPUTE POOL Identifier(''' || poolname || ''')
            FROM SPECIFICATION_FILE=''' || '/fullstack.yaml' || '''
            QUERY_WAREHOUSE=''' || whname || '''';
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