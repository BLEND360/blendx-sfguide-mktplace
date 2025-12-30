-- =============================================================================
-- APPLICATION LIFECYCLE PROCEDURES
-- start, stop, resume, update, destroy, alter compute pool
-- =============================================================================

-- =============================================================================
-- EXTERNAL ACCESS INTEGRATION (EAI) MANAGEMENT
-- Procedures to manage dynamic External Access Integrations
-- =============================================================================

-- Add a new external access configuration
CREATE OR REPLACE PROCEDURE app_public.add_external_access(
    eai_name VARCHAR,
    eai_label VARCHAR,
    eai_description VARCHAR,
    eai_host_ports VARCHAR
)
    RETURNS STRING
    LANGUAGE SQL
AS $$
BEGIN
    INSERT INTO app_data.external_access_configs (name, label, description, host_ports, enabled)
    VALUES (UPPER(:eai_name), :eai_label, :eai_description, :eai_host_ports, TRUE);
    RETURN 'External access config "' || UPPER(:eai_name) || '" added successfully';
END;
$$;

GRANT USAGE ON PROCEDURE app_public.add_external_access(VARCHAR, VARCHAR, VARCHAR, VARCHAR) TO APPLICATION ROLE app_admin;

-- Remove an external access configuration
CREATE OR REPLACE PROCEDURE app_public.remove_external_access(eai_name VARCHAR)
    RETURNS STRING
    LANGUAGE SQL
AS $$
BEGIN
    DELETE FROM app_data.external_access_configs WHERE name = UPPER(:eai_name);
    RETURN 'External access config "' || UPPER(:eai_name) || '" removed';
END;
$$;

GRANT USAGE ON PROCEDURE app_public.remove_external_access(VARCHAR) TO APPLICATION ROLE app_admin;

-- Enable/disable an external access configuration
CREATE OR REPLACE PROCEDURE app_public.toggle_external_access(eai_name VARCHAR, is_enabled BOOLEAN)
    RETURNS STRING
    LANGUAGE SQL
AS $$
BEGIN
    UPDATE app_data.external_access_configs SET enabled = :is_enabled WHERE name = UPPER(:eai_name);
    RETURN 'External access config "' || UPPER(:eai_name) || '" ' || CASE WHEN :is_enabled THEN 'enabled' ELSE 'disabled' END;
END;
$$;

GRANT USAGE ON PROCEDURE app_public.toggle_external_access(VARCHAR, BOOLEAN) TO APPLICATION ROLE app_admin;

-- List all external access configurations
CREATE OR REPLACE PROCEDURE app_public.list_external_access()
    RETURNS TABLE (name VARCHAR, label VARCHAR, description VARCHAR, host_ports VARCHAR, enabled BOOLEAN)
    LANGUAGE SQL
AS $$
DECLARE
    res RESULTSET;
BEGIN
    res := (SELECT name, label, description, host_ports, enabled FROM app_data.external_access_configs ORDER BY name);
    RETURN TABLE(res);
END;
$$;

GRANT USAGE ON PROCEDURE app_public.list_external_access() TO APPLICATION ROLE app_admin;

-- Create a single External Access Integration (Network Rule + EAI + Specification)
CREATE OR REPLACE PROCEDURE app_public.create_single_external_access(
    env_prefix VARCHAR,
    eai_config_name VARCHAR
)
    RETURNS STRING
    LANGUAGE SQL
AS $$
DECLARE
    config_label VARCHAR;
    config_desc VARCHAR;
    config_hosts VARCHAR;
    full_eai_name VARCHAR;
    full_rule_name VARCHAR;
    hosts_formatted VARCHAR;
BEGIN
    -- Get configuration from table
    SELECT label, description, host_ports
    INTO :config_label, :config_desc, :config_hosts
    FROM app_data.external_access_configs
    WHERE name = UPPER(:eai_config_name) AND enabled = TRUE;

    IF (config_hosts IS NULL) THEN
        RETURN 'EAI config "' || UPPER(:eai_config_name) || '" not found or disabled';
    END IF;

    -- Build names with prefix
    full_eai_name := CASE WHEN :env_prefix = '' THEN 'BLENDX_' || UPPER(:eai_config_name) || '_EAI'
                         ELSE UPPER(:env_prefix) || '_BLENDX_' || UPPER(:eai_config_name) || '_EAI' END;
    full_rule_name := CASE WHEN :env_prefix = '' THEN 'BLENDX_' || UPPER(:eai_config_name) || '_NETWORK_RULE'
                          ELSE UPPER(:env_prefix) || '_BLENDX_' || UPPER(:eai_config_name) || '_NETWORK_RULE' END;

    -- Format hosts for VALUE_LIST (handle comma-separated hosts)
    hosts_formatted := REPLACE(:config_hosts, ',', ''',''');

    -- Create Network Rule
    EXECUTE IMMEDIATE 'CREATE NETWORK RULE IF NOT EXISTS app_public.' || full_rule_name ||
        ' TYPE = HOST_PORT VALUE_LIST = (''' || hosts_formatted || ''') MODE = EGRESS';

    -- Create External Access Integration
    EXECUTE IMMEDIATE 'CREATE EXTERNAL ACCESS INTEGRATION IF NOT EXISTS ' || full_eai_name ||
        ' ALLOWED_NETWORK_RULES = (app_public.' || full_rule_name || ') ENABLED = TRUE';

    -- Set Application Specification for consumer approval
    EXECUTE IMMEDIATE 'ALTER APPLICATION SET SPECIFICATION ' || full_eai_name ||
        ' TYPE = EXTERNAL_ACCESS' ||
        ' LABEL = ''' || config_label || '''' ||
        ' DESCRIPTION = ''' || config_desc || '''' ||
        ' HOST_PORTS = (''' || hosts_formatted || ''')';

    RETURN 'Created EAI: ' || full_eai_name || ' with hosts: ' || :config_hosts;
END;
$$;

GRANT USAGE ON PROCEDURE app_public.create_single_external_access(VARCHAR, VARCHAR) TO APPLICATION ROLE app_admin;

-- Drop a single External Access Integration
CREATE OR REPLACE PROCEDURE app_public.drop_single_external_access(
    env_prefix VARCHAR,
    eai_config_name VARCHAR
)
    RETURNS STRING
    LANGUAGE SQL
AS $$
DECLARE
    full_eai_name VARCHAR;
    full_rule_name VARCHAR;
BEGIN
    -- Build names with prefix
    full_eai_name := CASE WHEN :env_prefix = '' THEN 'BLENDX_' || UPPER(:eai_config_name) || '_EAI'
                         ELSE UPPER(:env_prefix) || '_BLENDX_' || UPPER(:eai_config_name) || '_EAI' END;
    full_rule_name := CASE WHEN :env_prefix = '' THEN 'BLENDX_' || UPPER(:eai_config_name) || '_NETWORK_RULE'
                          ELSE UPPER(:env_prefix) || '_BLENDX_' || UPPER(:eai_config_name) || '_NETWORK_RULE' END;

    EXECUTE IMMEDIATE 'DROP EXTERNAL ACCESS INTEGRATION IF EXISTS ' || full_eai_name;
    EXECUTE IMMEDIATE 'DROP NETWORK RULE IF EXISTS app_public.' || full_rule_name;

    RETURN 'Dropped EAI: ' || full_eai_name || ' and network rule: ' || full_rule_name;
END;
$$;

GRANT USAGE ON PROCEDURE app_public.drop_single_external_access(VARCHAR, VARCHAR) TO APPLICATION ROLE app_admin;

-- =============================================================================
-- START APPLICATION
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
    wh_name VARCHAR;
    wh_size VARCHAR;
    pool_min NUMBER;
    pool_max NUMBER;
    eai_names_list VARCHAR DEFAULT '';
    eai_count NUMBER DEFAULT 0;
    eai_result VARCHAR;
    config_name VARCHAR;
    cur CURSOR FOR SELECT name FROM app_data.external_access_configs WHERE enabled = TRUE;
BEGIN
        -- Build resource names with optional environment prefix (all uppercase for consistency)
        poolname := CASE WHEN :env_prefix = '' THEN 'BLENDX_APP_COMPUTE_POOL' ELSE UPPER(:env_prefix) || '_BLENDX_APP_COMPUTE_POOL' END;
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

        -- Create all enabled External Access Integrations from config table
        OPEN cur;
        FOR record IN cur DO
            config_name := record.name;

            -- Create the EAI
            CALL app_public.create_single_external_access(:env_prefix, config_name) INTO :eai_result;

            -- Build the list of EAI names for the service
            IF (eai_names_list != '') THEN
                eai_names_list := eai_names_list || ', ';
            END IF;
            eai_names_list := eai_names_list ||
                CASE WHEN :env_prefix = '' THEN 'BLENDX_' || config_name || '_EAI'
                     ELSE UPPER(:env_prefix) || '_BLENDX_' || config_name || '_EAI' END;
            eai_count := eai_count + 1;
        END FOR;
        CLOSE cur;

        -- Create the service with all EAIs (warehouse is passed via QUERY_WAREHOUSE, backend detects it via CURRENT_WAREHOUSE())
        IF (eai_names_list != '') THEN
            EXECUTE IMMEDIATE 'CREATE SERVICE app_public.blendx_st_spcs IN COMPUTE POOL ' || poolname ||
                ' FROM SPECIFICATION_FILE=''/fullstack.yaml'' QUERY_WAREHOUSE=' || wh_name ||
                ' EXTERNAL_ACCESS_INTEGRATIONS = (' || eai_names_list || ')';
        ELSE
            -- No EAIs configured, create service without external access
            EXECUTE IMMEDIATE 'CREATE SERVICE app_public.blendx_st_spcs IN COMPUTE POOL ' || poolname ||
                ' FROM SPECIFICATION_FILE=''/fullstack.yaml'' QUERY_WAREHOUSE=' || wh_name;
        END IF;

        GRANT USAGE ON SERVICE app_public.blendx_st_spcs TO APPLICATION ROLE app_user;
        GRANT SERVICE ROLE app_public.blendx_st_spcs!ALL_ENDPOINTS_USAGE TO APPLICATION ROLE app_user;

        RETURN migration_verification || ' | ' || migration_status || '. Service started with pool ' || poolname || ' (min=' || pool_min || ', max=' || pool_max || '), warehouse ' || wh_name || ' (' || wh_size || ')' || ' and ' || eai_count || ' EAI(s): ' || eai_names_list || '. Check status, and when ready, get URL';
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
    full_eai_name VARCHAR;
    full_rule_name VARCHAR;
    config_name VARCHAR;
    eai_count NUMBER DEFAULT 0;
    cur CURSOR FOR SELECT name FROM app_data.external_access_configs;
BEGIN
    -- Build resource names with optional environment prefix (all uppercase for consistency)
    wh_name := CASE WHEN :env_prefix = '' THEN 'BLENDX_APP_WH' ELSE UPPER(:env_prefix) || '_BLENDX_APP_WH' END;

    -- Drop the service first
    DROP SERVICE IF EXISTS app_public.blendx_st_spcs;

    -- Drop the warehouse
    EXECUTE IMMEDIATE 'DROP WAREHOUSE IF EXISTS ' || wh_name;

    -- Drop all EAIs from config table
    OPEN cur;
    FOR record IN cur DO
        config_name := record.name;

        -- Build names with prefix
        full_eai_name := CASE WHEN :env_prefix = '' THEN 'BLENDX_' || config_name || '_EAI'
                             ELSE UPPER(:env_prefix) || '_BLENDX_' || config_name || '_EAI' END;
        full_rule_name := CASE WHEN :env_prefix = '' THEN 'BLENDX_' || config_name || '_NETWORK_RULE'
                              ELSE UPPER(:env_prefix) || '_BLENDX_' || config_name || '_NETWORK_RULE' END;

        EXECUTE IMMEDIATE 'DROP EXTERNAL ACCESS INTEGRATION IF EXISTS ' || full_eai_name;
        EXECUTE IMMEDIATE 'DROP NETWORK RULE IF EXISTS app_public.' || full_rule_name;
        eai_count := eai_count + 1;
    END FOR;
    CLOSE cur;

    RETURN 'Service destroyed, warehouse ' || wh_name || ' dropped, and ' || eai_count || ' EAI(s) with their network rules removed';
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
