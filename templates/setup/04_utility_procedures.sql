-- =============================================================================
-- UTILITY PROCEDURES
-- app_url, service logs, service status, crew executions
-- =============================================================================

CREATE OR REPLACE PROCEDURE app_public.app_url()
    RETURNS string
    LANGUAGE sql
    AS
$$
BEGIN
    LET ingress_url VARCHAR;
    SHOW ENDPOINTS IN SERVICE app_public.blendx_st_spcs;
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
    RETURN SYSTEM$GET_SERVICE_LOGS('app_public.blendx_st_spcs', 0, :container_name, :num_lines);
END
$$;
GRANT USAGE ON PROCEDURE app_public.get_service_logs(VARCHAR, NUMBER) TO APPLICATION ROLE app_admin;

CREATE OR REPLACE PROCEDURE app_public.get_service_status()
    RETURNS STRING
    LANGUAGE sql
    AS
$$
BEGIN
    RETURN SYSTEM$GET_SERVICE_STATUS('app_public.blendx_st_spcs');
END
$$;
GRANT USAGE ON PROCEDURE app_public.get_service_status() TO APPLICATION ROLE app_admin;

-- =============================================================================
-- CREW EXECUTION RESULTS PROCEDURES
-- =============================================================================

-- Procedure to get the last execution result
CREATE OR REPLACE PROCEDURE app_public.get_last_crew_execution()
    RETURNS TABLE (
        id VARCHAR,
        execution_timestamp TIMESTAMP_NTZ,
        updated_at TIMESTAMP_NTZ,
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

-- Procedure to get recent executions (last N)
CREATE OR REPLACE PROCEDURE app_public.get_recent_crew_executions(num_results NUMBER)
    RETURNS TABLE (
        id VARCHAR,
        execution_timestamp TIMESTAMP_NTZ,
        updated_at TIMESTAMP_NTZ,
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
