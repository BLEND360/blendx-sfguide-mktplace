-- =============================================================================
-- BLENDX APPLICATION SETUP SCRIPT
-- =============================================================================
-- This is the main setup script that orchestrates the application installation.
-- It uses EXECUTE IMMEDIATE FROM to load modular SQL files for better organization.
--
-- Script execution order:
-- 1. Schemas and roles setup
-- 2. Database migrations (auto-generated from Alembic)
-- 3. Application lifecycle procedures (start, stop, resume, destroy)
-- 4. Utility procedures (logs, status, crew executions)
-- 5. Configuration procedures (references, callbacks)
-- =============================================================================

-- 1. Schemas, roles, and basic permissions
EXECUTE IMMEDIATE FROM '/scripts/setup/01_schemas_roles.sql';

-- 2. Database migrations and migration procedures
EXECUTE IMMEDIATE FROM '/scripts/setup/02_migrations.sql';

-- 3. Application lifecycle procedures
EXECUTE IMMEDIATE FROM '/scripts/setup/03_app_lifecycle.sql';

-- 4. Utility procedures
EXECUTE IMMEDIATE FROM '/scripts/setup/04_utility_procedures.sql';

-- 5. Configuration procedures
EXECUTE IMMEDIATE FROM '/scripts/setup/05_config.sql';
