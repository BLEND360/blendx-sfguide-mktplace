-- =============================================================================
-- CONFIGURATION PROCEDURES
-- Reference callbacks for secrets and configuration
-- =============================================================================

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
