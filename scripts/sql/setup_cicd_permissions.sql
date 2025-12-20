-- ============================================================================
-- Script to configure CI/CD permissions for the deploy pipeline
-- Run with ACCOUNTADMIN role
-- ============================================================================

-- ============================================================================
-- CONFIGURATION - Update these values before running
-- ============================================================================
-- Role and User names
-- CICD_ROLE: MK_BLENDX_DEPLOY_ROLE
-- CICD_USER: MK_BLENDX_DEPLOY_USER

-- Database objects
-- DATABASE: BLENDX_APP
-- SCHEMA: NAPP
-- STAGE: APP_STAGE
-- IMAGE_REPO: img_repo
-- WAREHOUSE: DEV_WH

-- Note: Application Package will be created by the pipeline itself,
-- so the role will automatically have OWNERSHIP permissions on it.
-- ============================================================================

-- ============================================================================
-- 1. Create user for CI/CD with JWT authentication (key-pair)
-- ============================================================================
-- IMPORTANT: Before running this, you must generate an RSA key pair:
--
-- In your local terminal:
--   openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out snowflake_key.p8 -nocrypt
--   openssl rsa -in snowflake_key.p8 -pubout -out snowflake_key.pub
--
-- Then copy the content of snowflake_key.pub (without headers) for RSA_PUBLIC_KEY
-- The content of snowflake_key.p8 goes as secret SNOWFLAKE_PRIVATE_KEY_RAW in GitHub
-- ============================================================================

USE ROLE ACCOUNTADMIN;

-- Create the user (replace <PUBLIC_KEY_CONTENT> with your public key without headers)
CREATE USER IF NOT EXISTS MK_BLENDX_DEPLOY_USER
    TYPE = SERVICE
    COMMENT = 'User for CI/CD pipeline of marketplace app'
    RSA_PUBLIC_KEY = '<PASTE_YOUR_PUBLIC_KEY_WITHOUT_HEADERS_HERE>';

-- If the user already exists and you only need to update the key:
-- ALTER USER MK_BLENDX_DEPLOY_USER SET RSA_PUBLIC_KEY = '<PASTE_YOUR_PUBLIC_KEY_WITHOUT_HEADERS_HERE>';

-- ============================================================================
-- 2. Create the role for CI/CD
-- ============================================================================
CREATE ROLE IF NOT EXISTS MK_BLENDX_DEPLOY_ROLE;
GRANT ROLE MK_BLENDX_DEPLOY_ROLE TO USER MK_BLENDX_DEPLOY_USER;
GRANT ROLE MK_BLENDX_DEPLOY_ROLE TO ROLE BLENDX_TEAM;

-- Set default role and warehouse for the user
ALTER USER MK_BLENDX_DEPLOY_USER SET DEFAULT_ROLE = 'MK_BLENDX_DEPLOY_ROLE';
ALTER USER MK_BLENDX_DEPLOY_USER SET DEFAULT_WAREHOUSE = 'DEV_WH';

-- ============================================================================
-- 3. Warehouse permissions
-- ============================================================================
GRANT USAGE ON WAREHOUSE DEV_WH TO ROLE MK_BLENDX_DEPLOY_ROLE;

-- ============================================================================
-- 4. Database and Schema permissions
-- ============================================================================
GRANT USAGE ON DATABASE BLENDX_APP TO ROLE MK_BLENDX_DEPLOY_ROLE;
GRANT USAGE ON SCHEMA BLENDX_APP.NAPP TO ROLE MK_BLENDX_DEPLOY_ROLE;

-- ============================================================================
-- 5. Stage permissions (to upload app files)
-- ============================================================================
GRANT READ, WRITE ON STAGE BLENDX_APP.NAPP.APP_STAGE TO ROLE MK_BLENDX_DEPLOY_ROLE;

-- ============================================================================
-- 6. Image Repository permissions (for Docker image push)
-- ============================================================================
GRANT READ, WRITE ON IMAGE REPOSITORY BLENDX_APP.NAPP.img_repo TO ROLE MK_BLENDX_DEPLOY_ROLE;

-- ============================================================================
-- 7. Permission to create Application Packages
-- ============================================================================
-- The pipeline creates the Application Package, so it needs CREATE permission
GRANT CREATE APPLICATION PACKAGE ON ACCOUNT TO ROLE MK_BLENDX_DEPLOY_ROLE;

-- ============================================================================
-- 8. Permissions to manage the installed application (optional, for restart)
-- ============================================================================
-- If the pipeline needs to restart the application, it needs a role with permissions
-- on the installed application. This is usually a different role (NAC_ROLE).
--
-- If you use the same role for everything:
-- GRANT USAGE ON APPLICATION <APP_INSTANCE_NAME> TO ROLE MK_BLENDX_DEPLOY_ROLE;

-- ============================================================================
-- 9. Application grants (run AFTER first app installation)
-- ============================================================================
-- These grants allow the installed application to create compute resources.
-- Run these commands after the application is installed for the first time.
-- Replace <APP_INSTANCE_NAME> with the actual application instance name.
--
-- GRANT CREATE COMPUTE POOL ON ACCOUNT TO APPLICATION <APP_INSTANCE_NAME>;
-- GRANT BIND SERVICE ENDPOINT ON ACCOUNT TO APPLICATION <APP_INSTANCE_NAME>;
-- GRANT CREATE WAREHOUSE ON ACCOUNT TO APPLICATION <APP_INSTANCE_NAME>;

-- ============================================================================
-- 10. Verify assigned permissions
-- ============================================================================
SHOW GRANTS TO ROLE MK_BLENDX_DEPLOY_ROLE;

-- ============================================================================
-- GitHub Secrets to configure:
-- ============================================================================
-- SNOWFLAKE_ACCOUNT: Your Snowflake account identifier
-- SNOWFLAKE_HOST: Your Snowflake host (e.g., xxx.snowflakecomputing.com)
-- SNOWFLAKE_DEPLOY_USER: MK_BLENDX_DEPLOY_USER
-- SNOWFLAKE_DEPLOY_ROLE: MK_BLENDX_DEPLOY_ROLE
-- SNOWFLAKE_WAREHOUSE: DEV_WH
-- SNOWFLAKE_DATABASE: BLENDX_APP
-- SNOWFLAKE_SCHEMA: NAPP
-- SNOWFLAKE_REPO: url for image repo
-- SNOWFLAKE_PRIVATE_KEY_RAW: Content of snowflake_key.p8 file
-- SNOWFLAKE_REPO: Your image repository URL
-- SNOWFLAKE_APP_PACKAGE: Name for your app package (e.g., MK_BLENDX_APP_PKG)
-- SNOWFLAKE_APP_INSTANCE: Name of the installed app instance (for restart) e.g. BLENDX_APP_INSTANCE
-- SNOWFLAKE_COMPUTE_POOL: Compute pool for the app e.g BLENDX_CP
-- SNOWFLAKE_ROLE: Role with permissions on the installed app (optional) e.g. BLENDX_APP_ROLE
-- ============================================================================
