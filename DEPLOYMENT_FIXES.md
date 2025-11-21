# Deployment Fixes and Improvements

This document summarizes all the fixes and improvements made to the Snowflake Native App deployment process.

## Issues Found and Fixed

### 1. Setup.sql - GRANT Permission Issue

**Problem:** The `register_single_reference` procedure was granted to `APP_PUBLIC` instead of `APP_ADMIN`.

**File:** `app/src/setup.sql:225-227`

**Fix:**
```sql
GRANT USAGE
  ON PROCEDURE CONFIG.REGISTER_SINGLE_REFERENCE(STRING, STRING, STRING)
  TO APPLICATION ROLE APP_ADMIN;  -- Changed from APP_PUBLIC
```

**Impact:** This prevented proper configuration of secret references.

---

### 2. Missing Application Package Creation

**Problem:** The deployment scripts assumed the Application Package already existed.

**Scripts Affected:** `deploy.sh`, `initial-install.sh`

**Fix:** Created `complete-setup.sh` which creates the package first:
```bash
CREATE APPLICATION PACKAGE IF NOT EXISTS spcs_app_pkg_test;
```

---

### 3. Missing Permission Grants

**Problem:** The consumer role didn't have permissions to install/develop from the application package.

**Fix:** Added permission grants in `complete-setup.sh`:
```sql
GRANT INSTALL, DEVELOP ON APPLICATION PACKAGE spcs_app_pkg_test TO ROLE nac_test;
```

---

### 4. start_app Procedure - Identifier() Issue

**Problem:** The `start_app` procedure used `Identifier()` incorrectly in `EXECUTE IMMEDIATE`, causing compute pool resolution failures.

**File:** `app/src/setup.sql:35-58`

**Original Code:**
```sql
EXECUTE IMMEDIATE 'CREATE SERVICE IF NOT EXISTS app_public.st_spcs
    IN COMPUTE POOL Identifier(''' || poolname || ''')
    FROM SPECIFICATION_FILE=''' || '/fullstack.yaml' || '''
    QUERY_WAREHOUSE=''' || whname || '''';
```

**Fixed Code:**
```sql
EXECUTE IMMEDIATE 'CREATE SERVICE IF NOT EXISTS app_public.st_spcs
    IN COMPUTE POOL ' || poolname || '
    FROM SPECIFICATION_FILE=''' || '/fullstack.yaml' || '''
    QUERY_WAREHOUSE=' || whname;
```

**Impact:** Services could not start because compute pools couldn't be found.

---

### 5. start_app Procedure - Missing Compute Pool Creation

**Problem:** The procedure assumed compute pools already existed and didn't create them.

**File:** `app/src/setup.sql:40-45`

**Fix:** Added automatic compute pool creation:
```sql
-- First, create compute pool if it doesn't exist
EXECUTE IMMEDIATE 'CREATE COMPUTE POOL IF NOT EXISTS ' || poolname || '
    MIN_NODES = 1
    MAX_NODES = 3
    INSTANCE_FAMILY = CPU_X64_M
    AUTO_RESUME = TRUE';
```

**Impact:** Compute pools are now created automatically, ensuring service can start.

---

### 6. Secret Configuration

**Problem:** Secrets weren't being configured properly with the required permissions and the reference wasn't being registered.

**Fix:** Added comprehensive secret setup in `complete-setup.sh`:
```sql
-- Create secret infrastructure
CREATE DATABASE IF NOT EXISTS secrets_db;
CREATE SCHEMA IF NOT EXISTS secrets_db.app_secrets;
CREATE SECRET serper_api_key TYPE = GENERIC_STRING SECRET_STRING = 'value';

-- Grant permissions
GRANT REFERENCE_USAGE ON DATABASE secrets_db TO SHARE IN APPLICATION PACKAGE spcs_app_pkg_test;
GRANT READ ON SECRET secrets_db.app_secrets.serper_api_key TO APPLICATION spcs_app_instance_test;
GRANT USAGE ON DATABASE secrets_db TO APPLICATION spcs_app_instance_test;
GRANT USAGE ON SCHEMA secrets_db.app_secrets TO APPLICATION spcs_app_instance_test;

-- Register the secret reference (CRITICAL STEP)
CALL spcs_app_instance_test.config.register_single_reference('serper_api_key', 'ADD', 'secrets_db.app_secrets.serper_api_key');
```

**Impact:** Without calling `register_single_reference`, the application cannot access the external secret using `SYSTEM$REFERENCE()` even with proper permissions.

---

### 7. Warehouse Access

**Problem:** The application didn't have access to the warehouse needed for queries.

**Fix:** Added warehouse grant in `complete-setup.sh`:
```sql
GRANT USAGE ON WAREHOUSE WH_BLENDX_DEMO_PROVIDER TO APPLICATION spcs_app_instance_test;
```

---

## New Files Created

### 1. `scripts/complete-setup.sh`

A comprehensive setup script that performs a full deployment from scratch:

- Creates Application Package
- Grants permissions
- Sets up secrets
- Builds and deploys application
- Creates application instance
- Configures references
- Starts SPCS service

**Usage:**
```bash
./scripts/complete-setup.sh
```

---

## Updated Files

### 1. `app/src/setup.sql`

**Changes:**
- Fixed GRANT for `register_single_reference` (line 225-227)
- Fixed `start_app` procedure to remove `Identifier()` (line 40-51)
- Added automatic compute pool creation (line 40-45)

### 2. `scripts/README.md`

**Changes:**
- Added `complete-setup.sh` documentation
- Updated Quick Start section
- Added distinction between first-time and subsequent deployments
- Updated compute pool name in examples
- Added note about automatic compute pool creation

---

## Testing Checklist

After making these fixes, the following deployment flow now works:

- [ ] Run `complete-setup.sh` for first-time deployment
- [ ] Application package is created
- [ ] Permissions are granted correctly
- [ ] Secret is created and configured
- [ ] Docker images are built and pushed
- [ ] Application instance is created
- [ ] Service starts successfully
- [ ] Service reaches READY state
- [ ] Application URL is accessible

---

## Known Issues and Limitations

### 1. Secret Placeholder

The `complete-setup.sh` script creates secrets with a placeholder value. Users must update the secret with their actual Serper API key:

```bash
snow sql -q "USE ROLE nac_test; USE SCHEMA secrets_db.app_secrets; ALTER SECRET serper_api_key SET SECRET_STRING = 'YOUR_ACTUAL_API_KEY';" --connection mkt_blendx_demo
```

### 2. Compute Pool Naming

If a compute pool with the same name exists from a previous deployment, the `start_app` procedure will fail. Use a different pool name or clean up old pools.

### 3. Service Startup Time

SPCS services can take 2-5 minutes to reach READY state after starting. Monitor status with:

```bash
snow sql -q "USE ROLE nac_test; CALL spcs_app_instance_test.app_public.get_service_status();" --connection mkt_blendx_demo
```

---

## Deployment Best Practices

### For Development

1. Use `complete-setup.sh` for initial setup
2. Use `deploy.sh` for code changes
3. Monitor logs regularly:
   ```bash
   snow sql -q "USE ROLE nac_test; CALL spcs_app_instance_test.app_public.get_service_logs('eap-backend', 200);" --connection mkt_blendx_demo
   ```

### For Production

1. Use environment-specific `.env` files
2. Version your deployments (e.g., v1.0.0, v1.1.0)
3. Test in a staging environment first
4. Keep secrets separate from code
5. Use CI/CD pipelines for consistency

---

## Rollback Procedures

If deployment fails or causes issues:

### 1. Stop the Service
```bash
snow sql -q "USE ROLE nac_test; CALL spcs_app_instance_test.app_public.stop_app();" --connection mkt_blendx_demo
```

### 2. Drop the Application
```bash
snow sql -q "USE ROLE nac_test; DROP APPLICATION IF EXISTS spcs_app_instance_test;" --connection mkt_blendx_demo
```

### 3. Clean Up Application Package (if needed)
```bash
snow sql -q "USE ROLE naspcs_role; DROP APPLICATION PACKAGE IF EXISTS spcs_app_pkg_test;" --connection mkt_blendx_demo
```

### 4. Redeploy
```bash
./scripts/complete-setup.sh
```

---

## Future Improvements

Potential enhancements for the deployment process:

1. **Automated Testing** - Add integration tests to verify deployment
2. **Health Checks** - Implement automated health checking post-deployment
3. **Blue/Green Deployments** - Support zero-downtime deployments
4. **Secret Rotation** - Automate secret rotation procedures
5. **Monitoring Integration** - Add integration with monitoring tools
6. **Backup/Restore** - Implement backup and restore procedures

---

## References

- [Snowflake Native Apps Documentation](https://docs.snowflake.com/en/developer-guide/native-apps/native-apps-about)
- [SPCS Documentation](https://docs.snowflake.com/en/developer-guide/snowpark-container-services/overview)
- [Secret Management](https://docs.snowflake.com/en/developer-guide/native-apps/secret-reference)

---

## Change Log

### 2025-11-20 (Initial Fixes)

- Fixed `setup.sql` GRANT permissions
- Fixed `start_app` procedure compute pool resolution
- Added automatic compute pool creation
- Created `complete-setup.sh` script
- Updated documentation

### 2025-11-20 (Additional Fixes)

- Fixed `SYSTEM$REFERENCE()` call in `fastapi_app.py` to include 'secret' parameter
- Fixed application existence check in both `deploy.sh` and `complete-setup.sh` (grep was matching SQL statement)
- Added missing `register_single_reference` call to properly register external secret with application

---

## Support

For issues or questions:

1. Check the [Troubleshooting](scripts/README.md#troubleshooting) section
2. Review service logs for errors
3. Verify all prerequisites are met
4. Contact the development team
