-- =============================================================================
-- APPLICATION LIFECYCLE PROCEDURES
-- start, stop, resume, update, destroy, alter compute pool
-- =============================================================================

-- Internal procedure with env_prefix, warehouse_size, and compute pool parameters (use start_application wrapper instead)
CREATE OR REPLACE PROCEDURE app_public.start_application_internal(env_prefix VARCHAR, warehouse_size VARCHAR, cp_min_nodes NUMBER, cp_max_nodes NUMBER)
    RETURNS string
    LANGUAGE sql
    AS $$
DECLARE
    migration_status VARCHAR;
    migration_verification VARCHAR;
    poolname VARCHAR;
    eai_name VARCHAR;
    network_rule_name VARCHAR;
    wh_name VARCHAR;
    wh_size VARCHAR;
    pool_min NUMBER;
    pool_max NUMBER;
BEGIN
        -- Build resource names with optional environment prefix (all uppercase for consistency)
        poolname := CASE WHEN :env_prefix = '' THEN 'BLENDX_APP_COMPUTE_POOL' ELSE UPPER(:env_prefix) || '_BLENDX_APP_COMPUTE_POOL' END;
        eai_name := CASE WHEN :env_prefix = '' THEN 'BLENDX_SERPER_EAI' ELSE UPPER(:env_prefix) || '_BLENDX_SERPER_EAI' END;
        network_rule_name := CASE WHEN :env_prefix = '' THEN 'BLENDX_SERPER_NETWORK_RULE' ELSE UPPER(:env_prefix) || '_BLENDX_SERPER_NETWORK_RULE' END;
        wh_name := CASE WHEN :env_prefix = '' THEN 'BLENDX_APP_WH' ELSE UPPER(:env_prefix) || '_BLENDX_APP_WH' END;

        -- Default warehouse size to X-SMALL if not provided
        wh_size := CASE WHEN :warehouse_size = '' OR :warehouse_size IS NULL THEN 'X-SMALL' ELSE :warehouse_size END;

        -- Default compute pool min/max nodes if not provided (0 or NULL means use default)
        pool_min := CASE WHEN :cp_min_nodes IS NULL OR :cp_min_nodes <= 0 THEN 1 ELSE :cp_min_nodes END;
        pool_max := CASE WHEN :cp_max_nodes IS NULL OR :cp_max_nodes <= 0 THEN 3 ELSE :cp_max_nodes END;

        -- Verify all migrations are applied (migrations are idempotent via setup.sql DDL)
        CALL app_data.verify_migrations() INTO :migration_verification;
        CALL app_data.get_migration_status() INTO :migration_status;

        -- First, create the application warehouse (unique name per app to avoid conflicts)
        EXECUTE IMMEDIATE 'CREATE WAREHOUSE IF NOT EXISTS ' || wh_name ||
            ' WAREHOUSE_SIZE = ''' || wh_size || ''' ' ||
            'AUTO_SUSPEND = 60 ' ||
            'AUTO_RESUME = TRUE ' ||
            'INITIALLY_SUSPENDED = TRUE';

        -- Grant usage on warehouse to application roles so SPCS service can use it
        EXECUTE IMMEDIATE 'GRANT USAGE ON WAREHOUSE ' || wh_name || ' TO APPLICATION ROLE app_admin';
        EXECUTE IMMEDIATE 'GRANT USAGE ON WAREHOUSE ' || wh_name || ' TO APPLICATION ROLE app_user';

        -- Create compute pool if it doesn't exist
        EXECUTE IMMEDIATE 'CREATE COMPUTE POOL IF NOT EXISTS ' || poolname ||
            ' MIN_NODES = ' || pool_min || ' MAX_NODES = ' || pool_max || ' INSTANCE_FAMILY = CPU_X64_M AUTO_RESUME = TRUE AUTO_SUSPEND_SECS = 300';

        -- Create network rule for Serper API access (prefixed to avoid conflicts)
        EXECUTE IMMEDIATE 'CREATE NETWORK RULE IF NOT EXISTS app_public.' || network_rule_name ||
            ' TYPE = HOST_PORT VALUE_LIST = (''google.serper.dev'') MODE = EGRESS';

        -- Create external access integration for Serper API (prefixed to avoid conflicts)
        EXECUTE IMMEDIATE 'CREATE EXTERNAL ACCESS INTEGRATION IF NOT EXISTS ' || eai_name ||
            ' ALLOWED_NETWORK_RULES = (app_public.' || network_rule_name || ') ENABLED = TRUE';

        -- Create the service (warehouse is passed via QUERY_WAREHOUSE, backend detects it via CURRENT_WAREHOUSE())
        EXECUTE IMMEDIATE 'CREATE SERVICE app_public.blendx_st_spcs IN COMPUTE POOL ' || poolname ||
            ' FROM SPECIFICATION_FILE=''/fullstack.yaml'' QUERY_WAREHOUSE=' || wh_name ||
            ' EXTERNAL_ACCESS_INTEGRATIONS = (' || eai_name || ')';

        GRANT USAGE ON SERVICE app_public.blendx_st_spcs TO APPLICATION ROLE app_user;
        GRANT SERVICE ROLE app_public.blendx_st_spcs!ALL_ENDPOINTS_USAGE TO APPLICATION ROLE app_user;

        RETURN migration_verification || ' | ' || migration_status || '. Service started with pool ' || poolname || ' (min=' || pool_min || ', max=' || pool_max || '), warehouse ' || wh_name || ' (' || wh_size || ')' || ' and EAI ' || eai_name || '. Check status, and when ready, get URL';
END;
$$;

GRANT USAGE ON PROCEDURE app_public.start_application_internal(VARCHAR, VARCHAR, NUMBER, NUMBER) TO APPLICATION ROLE app_admin;

-- Public wrapper: start_application() - uses default resource names, X-SMALL warehouse, and default compute pool (1-3 nodes)
CREATE OR REPLACE PROCEDURE app_public.start_application()
    RETURNS string
    LANGUAGE sql
    AS $$
DECLARE
    result VARCHAR;
BEGIN
    CALL app_public.start_application_internal('', 'X-SMALL', NULL, NULL) INTO :result;
    RETURN result;
END;
$$;

GRANT USAGE ON PROCEDURE app_public.start_application() TO APPLICATION ROLE app_admin;

-- Public wrapper: start_application(warehouse_size) - uses default names with custom warehouse size
CREATE OR REPLACE PROCEDURE app_public.start_application(warehouse_size VARCHAR)
    RETURNS string
    LANGUAGE sql
    AS $$
DECLARE
    result VARCHAR;
BEGIN
    CALL app_public.start_application_internal('', :warehouse_size, NULL, NULL) INTO :result;
    RETURN result;
END;
$$;

GRANT USAGE ON PROCEDURE app_public.start_application(VARCHAR) TO APPLICATION ROLE app_admin;

-- Public wrapper: start_application(warehouse_size, min_nodes, max_nodes) - custom warehouse and compute pool
CREATE OR REPLACE PROCEDURE app_public.start_application(warehouse_size VARCHAR, min_nodes NUMBER, max_nodes NUMBER)
    RETURNS string
    LANGUAGE sql
    AS $$
DECLARE
    result VARCHAR;
BEGIN
    CALL app_public.start_application_internal('', :warehouse_size, :min_nodes, :max_nodes) INTO :result;
    RETURN result;
END;
$$;

GRANT USAGE ON PROCEDURE app_public.start_application(VARCHAR, NUMBER, NUMBER) TO APPLICATION ROLE app_admin;

-- Public wrapper: start_application_with_prefix(env_prefix) - uses prefixed resource names with default warehouse size
CREATE OR REPLACE PROCEDURE app_public.start_application_with_prefix(env_prefix VARCHAR)
    RETURNS string
    LANGUAGE sql
    AS $$
DECLARE
    result VARCHAR;
BEGIN
    CALL app_public.start_application_internal(:env_prefix, 'X-SMALL', NULL, NULL) INTO :result;
    RETURN result;
END;
$$;

GRANT USAGE ON PROCEDURE app_public.start_application_with_prefix(VARCHAR) TO APPLICATION ROLE app_admin;

-- Public wrapper: start_application_with_prefix(env_prefix, warehouse_size) - uses prefixed names with custom warehouse size
CREATE OR REPLACE PROCEDURE app_public.start_application_with_prefix(env_prefix VARCHAR, warehouse_size VARCHAR)
    RETURNS string
    LANGUAGE sql
    AS $$
DECLARE
    result VARCHAR;
BEGIN
    CALL app_public.start_application_internal(:env_prefix, :warehouse_size, NULL, NULL) INTO :result;
    RETURN result;
END;
$$;

GRANT USAGE ON PROCEDURE app_public.start_application_with_prefix(VARCHAR, VARCHAR) TO APPLICATION ROLE app_admin;

-- Public wrapper: start_application_with_prefix(env_prefix, warehouse_size, min_nodes, max_nodes) - full customization
CREATE OR REPLACE PROCEDURE app_public.start_application_with_prefix(env_prefix VARCHAR, warehouse_size VARCHAR, min_nodes NUMBER, max_nodes NUMBER)
    RETURNS string
    LANGUAGE sql
    AS $$
DECLARE
    result VARCHAR;
BEGIN
    CALL app_public.start_application_internal(:env_prefix, :warehouse_size, :min_nodes, :max_nodes) INTO :result;
    RETURN result;
END;
$$;

GRANT USAGE ON PROCEDURE app_public.start_application_with_prefix(VARCHAR, VARCHAR, NUMBER, NUMBER) TO APPLICATION ROLE app_admin;

-- =============================================================================
-- STOP / RESUME / UPDATE SERVICE
-- =============================================================================

CREATE OR REPLACE PROCEDURE app_public.stop_app()
    RETURNS string
    LANGUAGE sql
    AS
$$
BEGIN
    ALTER SERVICE app_public.blendx_st_spcs SUSPEND;
    RETURN 'Service suspended';
END
$$;
GRANT USAGE ON PROCEDURE app_public.stop_app() TO APPLICATION ROLE app_admin;

CREATE OR REPLACE PROCEDURE app_public.resume_app()
    RETURNS string
    LANGUAGE sql
    AS
$$
BEGIN
    ALTER SERVICE app_public.blendx_st_spcs RESUME;
    RETURN 'Service resumed';
END
$$;
GRANT USAGE ON PROCEDURE app_public.resume_app() TO APPLICATION ROLE app_admin;

CREATE OR REPLACE PROCEDURE app_public.update_service()
    RETURNS string
    LANGUAGE sql
    AS
$$
BEGIN
    -- Reload service from specification file to pick up new image tags
    ALTER SERVICE app_public.blendx_st_spcs FROM SPECIFICATION_FILE='/fullstack.yaml';
    RETURN 'Service updated with new specification';
END
$$;
GRANT USAGE ON PROCEDURE app_public.update_service() TO APPLICATION ROLE app_admin;

-- =============================================================================
-- ALTER COMPUTE POOL
-- =============================================================================

-- Internal procedure to alter compute pool settings (use alter_compute_pool wrapper instead)
CREATE OR REPLACE PROCEDURE app_public.alter_compute_pool_internal(env_prefix VARCHAR, min_nodes NUMBER, max_nodes NUMBER)
    RETURNS string
    LANGUAGE sql
    AS
$$
DECLARE
    poolname VARCHAR;
    alter_stmt VARCHAR;
BEGIN
    -- Build compute pool name with optional environment prefix
    poolname := CASE WHEN :env_prefix = '' THEN 'BLENDX_APP_COMPUTE_POOL' ELSE UPPER(:env_prefix) || '_BLENDX_APP_COMPUTE_POOL' END;

    -- Build ALTER statement based on provided parameters
    alter_stmt := 'ALTER COMPUTE POOL ' || poolname;

    IF (:min_nodes IS NOT NULL AND :min_nodes > 0) THEN
        alter_stmt := alter_stmt || ' SET MIN_NODES = ' || :min_nodes;
    END IF;

    IF (:max_nodes IS NOT NULL AND :max_nodes > 0) THEN
        alter_stmt := alter_stmt || ' MAX_NODES = ' || :max_nodes;
    END IF;

    -- Execute the alter statement
    EXECUTE IMMEDIATE alter_stmt;

    RETURN 'Compute pool ' || poolname || ' updated: MIN_NODES=' || COALESCE(:min_nodes::VARCHAR, 'unchanged') || ', MAX_NODES=' || COALESCE(:max_nodes::VARCHAR, 'unchanged');
END
$$;
GRANT USAGE ON PROCEDURE app_public.alter_compute_pool_internal(VARCHAR, NUMBER, NUMBER) TO APPLICATION ROLE app_admin;

-- Public wrapper: alter_compute_pool(min_nodes, max_nodes) - alter default compute pool
CREATE OR REPLACE PROCEDURE app_public.alter_compute_pool(min_nodes NUMBER, max_nodes NUMBER)
    RETURNS string
    LANGUAGE sql
    AS
$$
DECLARE
    result VARCHAR;
BEGIN
    CALL app_public.alter_compute_pool_internal('', :min_nodes, :max_nodes) INTO :result;
    RETURN result;
END
$$;
GRANT USAGE ON PROCEDURE app_public.alter_compute_pool(NUMBER, NUMBER) TO APPLICATION ROLE app_admin;

-- Public wrapper: alter_compute_pool_with_prefix(env_prefix, min_nodes, max_nodes) - alter prefixed compute pool
CREATE OR REPLACE PROCEDURE app_public.alter_compute_pool_with_prefix(env_prefix VARCHAR, min_nodes NUMBER, max_nodes NUMBER)
    RETURNS string
    LANGUAGE sql
    AS
$$
DECLARE
    result VARCHAR;
BEGIN
    CALL app_public.alter_compute_pool_internal(:env_prefix, :min_nodes, :max_nodes) INTO :result;
    RETURN result;
END
$$;
GRANT USAGE ON PROCEDURE app_public.alter_compute_pool_with_prefix(VARCHAR, NUMBER, NUMBER) TO APPLICATION ROLE app_admin;

-- =============================================================================
-- DESTROY APP
-- =============================================================================

-- Internal procedure with env_prefix parameter for destroy (use destroy_app wrapper instead)
CREATE OR REPLACE PROCEDURE app_public.destroy_app_internal(env_prefix VARCHAR)
    RETURNS string
    LANGUAGE sql
    AS
$$
DECLARE
    wh_name VARCHAR;
    eai_name VARCHAR;
    network_rule_name VARCHAR;
BEGIN
    -- Build resource names with optional environment prefix (all uppercase for consistency)
    wh_name := CASE WHEN :env_prefix = '' THEN 'BLENDX_APP_WH' ELSE UPPER(:env_prefix) || '_BLENDX_APP_WH' END;
    eai_name := CASE WHEN :env_prefix = '' THEN 'BLENDX_SERPER_EAI' ELSE UPPER(:env_prefix) || '_BLENDX_SERPER_EAI' END;
    network_rule_name := CASE WHEN :env_prefix = '' THEN 'BLENDX_SERPER_NETWORK_RULE' ELSE UPPER(:env_prefix) || '_BLENDX_SERPER_NETWORK_RULE' END;

    DROP SERVICE IF EXISTS app_public.blendx_st_spcs;
    EXECUTE IMMEDIATE 'DROP WAREHOUSE IF EXISTS ' || wh_name;
    EXECUTE IMMEDIATE 'DROP EXTERNAL ACCESS INTEGRATION IF EXISTS ' || eai_name;
    EXECUTE IMMEDIATE 'DROP NETWORK RULE IF EXISTS app_public.' || network_rule_name;
    RETURN 'Service, warehouse ' || wh_name || ', EAI ' || eai_name || ', and network rule ' || network_rule_name || ' destroyed';
END
$$;
GRANT USAGE ON PROCEDURE app_public.destroy_app_internal(VARCHAR) TO APPLICATION ROLE app_admin;

-- Public wrapper: destroy_app() - destroys service and default warehouse
CREATE OR REPLACE PROCEDURE app_public.destroy_app()
    RETURNS string
    LANGUAGE sql
    AS
$$
DECLARE
    result VARCHAR;
BEGIN
    CALL app_public.destroy_app_internal('') INTO :result;
    RETURN result;
END
$$;
GRANT USAGE ON PROCEDURE app_public.destroy_app() TO APPLICATION ROLE app_admin;

-- Public wrapper: destroy_app_with_prefix(env_prefix) - destroys service and prefixed warehouse
CREATE OR REPLACE PROCEDURE app_public.destroy_app_with_prefix(env_prefix VARCHAR)
    RETURNS string
    LANGUAGE sql
    AS
$$
DECLARE
    result VARCHAR;
BEGIN
    CALL app_public.destroy_app_internal(:env_prefix) INTO :result;
    RETURN result;
END
$$;
GRANT USAGE ON PROCEDURE app_public.destroy_app_with_prefix(VARCHAR) TO APPLICATION ROLE app_admin;
