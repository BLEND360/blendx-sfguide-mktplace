CREATE SCHEMA IF NOT EXISTS config;
GRANT USAGE ON SCHEMA config TO APPLICATION ROLE app_admin;
CREATE APPLICATION ROLE IF NOT EXISTS app_admin;
CREATE APPLICATION ROLE IF NOT EXISTS app_user;
CREATE SCHEMA IF NOT EXISTS app_public;
GRANT USAGE ON SCHEMA app_public TO APPLICATION ROLE app_admin;
GRANT USAGE ON SCHEMA app_public TO APPLICATION ROLE app_user;
CREATE OR ALTER VERSIONED SCHEMA v1;
GRANT USAGE ON SCHEMA v1 TO APPLICATION ROLE app_admin;


-- -- Callback procedure for External Access Integration registration
-- CREATE OR REPLACE PROCEDURE v1.register_external_access(ref_name STRING, operation STRING, ref_or_alias STRING)
-- RETURNS STRING
-- LANGUAGE SQL
-- AS
-- $$
--   BEGIN
--     CASE (operation)
--       WHEN 'ADD' THEN
--         SELECT SYSTEM$SET_REFERENCE(:ref_name, :ref_or_alias);
--       WHEN 'REMOVE' THEN
--         SELECT SYSTEM$REMOVE_REFERENCE(:ref_name);
--       WHEN 'CLEAR' THEN
--         SELECT SYSTEM$REMOVE_REFERENCE(:ref_name);
--       ELSE
--         RETURN 'Unknown operation: ' || operation;
--     END CASE;
--     RETURN 'Operation ' || operation || ' for ' || ref_name || ' succeeded.';
--   END;
-- $$;
-- GRANT USAGE ON PROCEDURE v1.register_external_access(STRING, STRING, STRING) TO APPLICATION ROLE app_admin;

-- -- Configuration callback for External Access Integration
-- CREATE OR REPLACE PROCEDURE v1.configure_external_access(ref_name STRING)
-- RETURNS STRING
-- LANGUAGE SQL
-- AS
-- $$
--   BEGIN
--     CASE (UPPER(ref_name))
--       WHEN 'CORTEX_REST_EAI' THEN
--         RETURN OBJECT_CONSTRUCT(
--           'type', 'CONFIGURATION',
--           'payload', OBJECT_CONSTRUCT(
--             'host_ports', ARRAY_CONSTRUCT('*.snowflakecomputing.com'),
--             'allowed_secrets', 'NONE')
--         )::STRING;
--       ELSE
--         RETURN '';
--     END CASE;
--   END;
-- $$;
-- GRANT USAGE ON PROCEDURE v1.configure_external_access(STRING) TO APPLICATION ROLE app_admin;


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