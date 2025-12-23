#!/bin/bash

# Provider Setup Script - Initial Setup for CI/CD Pipeline
# This script should be run ONCE by an ACCOUNTADMIN to setup:
# 1. Database, Schema, Stage, and Image Repository
# 2. CI/CD User with JWT authentication
# 3. CI/CD Role with necessary permissions
# 4. Application Package permissions (pipeline will create the package)
#
# After this, the GitHub Actions pipeline will handle all deployments.

set -e  # Exit on error

# ============================================
# Script Setup
# ============================================

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ============================================
# Configuration - UPDATE THESE VALUES
# ============================================

SNOW_CONNECTION=${SNOW_CONNECTION:-"mkt_blendx_demo"}

# CI/CD User and Role
CICD_USER=${CICD_USER:-"MK_BLENDX_DEPLOY_USER"}
CICD_ROLE=${CICD_ROLE:-"MK_BLENDX_DEPLOY_ROLE"}

# Database objects
DATABASE_NAME=${DATABASE_NAME:-"BLENDX_APP_DB"}
SCHEMA_NAME=${SCHEMA_NAME:-"BLENDX_SCHEMA"}
STAGE_NAME=${STAGE_NAME:-"APP_STAGE"}
IMAGE_REPO_NAME=${IMAGE_REPO_NAME:-"img_repo"}
WAREHOUSE_NAME=${WAREHOUSE_NAME:-"BLENDX_APP_WH"}

# Application Package (optional - pipeline can create this)
APP_PACKAGE_NAME=${APP_PACKAGE_NAME:-"MK_BLENDX_APP_PKG"}

# Consumer role (for app installation permissions)
APP_CONSUMER_ROLE=${APP_CONSUMER_ROLE:-"BLENDX_APP_ROLE"}

# Path to public key file
PUBLIC_KEY_FILE=${PUBLIC_KEY_FILE:-"$PROJECT_ROOT/keys/pipeline/snowflake_key.pub"}

# ============================================
# Helper Functions
# ============================================

log_step() {
    echo ""
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}========================================${NC}"
}

log_info() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

run_sql() {
    local description=$1
    local sql=$2
    echo -e "${BLUE}▶${NC} $description"
    snow sql -q "$sql" --connection ${SNOW_CONNECTION}
}

run_sql_silent() {
    local sql=$1
    snow sql -q "$sql" --connection ${SNOW_CONNECTION} 2>/dev/null || true
}

# ============================================
# Pre-flight Checks
# ============================================

log_step "Pre-flight Checks"

# Check if public key file exists
if [ ! -f "$PUBLIC_KEY_FILE" ]; then
    log_error "Public key file not found: $PUBLIC_KEY_FILE"
    echo ""
    echo "Please generate RSA keys first:"
    echo ""
    echo "  mkdir -p $PROJECT_ROOT/keys/pipeline"
    echo "  openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out $PROJECT_ROOT/keys/pipeline/snowflake_key.p8 -nocrypt"
    echo "  openssl rsa -in $PROJECT_ROOT/keys/pipeline/snowflake_key.p8 -pubout -out $PROJECT_ROOT/keys/pipeline/snowflake_key.pub"
    echo ""
    exit 1
fi

# Read public key content (remove headers and newlines)
PUBLIC_KEY_CONTENT=$(cat "$PUBLIC_KEY_FILE" | grep -v "BEGIN PUBLIC KEY" | grep -v "END PUBLIC KEY" | tr -d '\n')

if [ -z "$PUBLIC_KEY_CONTENT" ]; then
    log_error "Could not read public key content from $PUBLIC_KEY_FILE"
    exit 1
fi

log_info "Public key file found and valid"

# ============================================
# Display Configuration
# ============================================

echo ""
echo "=========================================="
echo "Provider Setup - CI/CD Configuration"
echo "=========================================="
echo ""
echo "Configuration:"
echo "  Connection: $SNOW_CONNECTION"
echo "  CI/CD User: $CICD_USER"
echo "  CI/CD Role: $CICD_ROLE"
echo "  Database: $DATABASE_NAME"
echo "  Schema: $SCHEMA_NAME"
echo "  Stage: $STAGE_NAME"
echo "  Image Repo: $IMAGE_REPO_NAME"
echo "  Warehouse: $WAREHOUSE_NAME"
echo "  App Package: $APP_PACKAGE_NAME"
echo "  Public Key: $PUBLIC_KEY_FILE"
echo ""

read -p "Continue with setup? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Setup cancelled."
    exit 0
fi

# ============================================
# Step 1: Create Database Infrastructure
# ============================================

log_step "Step 1: Creating Database Infrastructure"

run_sql "Creating warehouse" \
    "USE ROLE ACCOUNTADMIN;
     CREATE WAREHOUSE IF NOT EXISTS ${WAREHOUSE_NAME}
         WAREHOUSE_SIZE = 'XSMALL'
         AUTO_SUSPEND = 60
         AUTO_RESUME = TRUE
         COMMENT = 'Warehouse for BlendX CI/CD pipeline';"

run_sql "Creating database" \
    "USE ROLE ACCOUNTADMIN;
     CREATE DATABASE IF NOT EXISTS ${DATABASE_NAME};"

run_sql "Creating schema" \
    "USE ROLE ACCOUNTADMIN;
     CREATE SCHEMA IF NOT EXISTS ${DATABASE_NAME}.${SCHEMA_NAME};"

run_sql "Creating stage" \
    "USE ROLE ACCOUNTADMIN;
     CREATE STAGE IF NOT EXISTS ${DATABASE_NAME}.${SCHEMA_NAME}.${STAGE_NAME};"

run_sql "Creating image repository" \
    "USE ROLE ACCOUNTADMIN;
     CREATE IMAGE REPOSITORY IF NOT EXISTS ${DATABASE_NAME}.${SCHEMA_NAME}.${IMAGE_REPO_NAME};"

log_info "Database infrastructure created (including warehouse)"

# ============================================
# Step 2: Create CI/CD User
# ============================================

log_step "Step 2: Creating CI/CD User"

run_sql "Creating CI/CD user" \
    "USE ROLE ACCOUNTADMIN;
     CREATE USER IF NOT EXISTS ${CICD_USER}
         TYPE = SERVICE
         COMMENT = 'User for CI/CD pipeline of marketplace app'
         RSA_PUBLIC_KEY = '${PUBLIC_KEY_CONTENT}';"

log_info "CI/CD user created"

# ============================================
# Step 3: Create CI/CD Role
# ============================================

log_step "Step 3: Creating CI/CD Role"

run_sql "Creating CI/CD role" \
    "USE ROLE ACCOUNTADMIN;
     CREATE ROLE IF NOT EXISTS ${CICD_ROLE};"

run_sql "Creating App Consumer role" \
    "USE ROLE ACCOUNTADMIN;
     CREATE ROLE IF NOT EXISTS ${APP_CONSUMER_ROLE};"

run_sql "Granting CREATE APPLICATION to consumer role" \
    "USE ROLE ACCOUNTADMIN;
     GRANT CREATE APPLICATION ON ACCOUNT TO ROLE ${APP_CONSUMER_ROLE};"

run_sql "Granting CI/CD role to user" \
    "USE ROLE ACCOUNTADMIN;
     GRANT ROLE ${CICD_ROLE} TO USER ${CICD_USER};USE ROLE ACCOUNTADMIN; GRANT ROLE ${APP_CONSUMER_ROLE} TO ROLE ${CICD_ROLE};"

run_sql "Granting App Consumer role to CI/CD role" \
    "USE ROLE ACCOUNTADMIN;
     GRANT ROLE ${APP_CONSUMER_ROLE} TO ROLE ${CICD_ROLE};"

run_sql "Setting default role and warehouse" \
    "USE ROLE ACCOUNTADMIN;
     ALTER USER ${CICD_USER} SET DEFAULT_ROLE = '${CICD_ROLE}';
     ALTER USER ${CICD_USER} SET DEFAULT_WAREHOUSE = '${WAREHOUSE_NAME}';"

log_info "CI/CD and App Consumer roles created and assigned"

# ============================================
# Step 4: Grant Warehouse Permissions
# ============================================

log_step "Step 4: Granting Warehouse Permissions"

run_sql "Granting warehouse usage to CI/CD role" \
    "USE ROLE ACCOUNTADMIN;
     GRANT USAGE ON WAREHOUSE ${WAREHOUSE_NAME} TO ROLE ${CICD_ROLE};"

run_sql "Granting warehouse usage to App Consumer role" \
    "USE ROLE ACCOUNTADMIN;
     GRANT USAGE ON WAREHOUSE ${WAREHOUSE_NAME} TO ROLE ${APP_CONSUMER_ROLE};"

log_info "Warehouse permissions granted"

# ============================================
# Step 5: Grant Database and Schema Permissions
# ============================================

log_step "Step 5: Granting Database and Schema Permissions"

run_sql "Granting database usage" \
    "USE ROLE ACCOUNTADMIN;
     GRANT USAGE ON DATABASE ${DATABASE_NAME} TO ROLE ${CICD_ROLE};"

run_sql "Granting schema usage" \
    "USE ROLE ACCOUNTADMIN;
     GRANT USAGE ON SCHEMA ${DATABASE_NAME}.${SCHEMA_NAME} TO ROLE ${CICD_ROLE};"

log_info "Database and schema permissions granted"

# ============================================
# Step 6: Grant Stage Permissions
# ============================================

log_step "Step 6: Granting Stage Permissions"

run_sql "Granting stage read/write" \
    "USE ROLE ACCOUNTADMIN;
     GRANT READ, WRITE ON STAGE ${DATABASE_NAME}.${SCHEMA_NAME}.${STAGE_NAME} TO ROLE ${CICD_ROLE};"

log_info "Stage permissions granted"

# ============================================
# Step 7: Grant Image Repository Permissions
# ============================================

log_step "Step 7: Granting Image Repository Permissions"

run_sql "Granting image repository read/write" \
    "USE ROLE ACCOUNTADMIN;
     GRANT READ, WRITE ON IMAGE REPOSITORY ${DATABASE_NAME}.${SCHEMA_NAME}.${IMAGE_REPO_NAME} TO ROLE ${CICD_ROLE};"

log_info "Image repository permissions granted"

# ============================================
# Step 8: Grant Application Package Creation Permission
# ============================================

log_step "Step 8: Granting Application Package Creation Permission"

run_sql "Granting create application package" \
    "USE ROLE ACCOUNTADMIN;
     GRANT CREATE APPLICATION PACKAGE ON ACCOUNT TO ROLE ${CICD_ROLE};"

log_info "Application package creation permission granted"

# ============================================
# Step 9: Verify Permissions
# ============================================

log_step "Step 9: Verifying Permissions"

run_sql "Showing grants to CI/CD role" \
    "SHOW GRANTS TO ROLE ${CICD_ROLE};"

# ============================================
# Completion Message
# ============================================

echo ""
echo "=========================================="
echo -e "${GREEN}Provider Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "GitHub Secrets to configure:"
echo ""
echo "  SNOWFLAKE_ACCOUNT: <your-account-identifier>"
echo "  SNOWFLAKE_HOST: <your-account>.snowflakecomputing.com"
echo "  SNOWFLAKE_PRIVATE_KEY_RAW: <content of keys/pipeline/snowflake_key.p8>"
echo ""
echo "GitHub Variables to configure:"
echo ""
echo "  SNOWFLAKE_CONNECTION: ${SNOW_CONNECTION}"
echo "  SNOWFLAKE_DEPLOY_USER: ${CICD_USER}"
echo "  SNOWFLAKE_DEPLOY_ROLE: ${CICD_ROLE}"
echo "  SNOWFLAKE_WAREHOUSE: ${WAREHOUSE_NAME}"
echo "  SNOWFLAKE_DATABASE: ${DATABASE_NAME}"
echo "  SNOWFLAKE_SCHEMA: ${SCHEMA_NAME}"
echo "  SNOWFLAKE_REPO: <your-image-repo-url>"
echo "  SNOWFLAKE_APP_PACKAGE: ${APP_PACKAGE_NAME}"
echo "  SNOWFLAKE_APP_INSTANCE: BLENDX_APP_INSTANCE"
echo "  SNOWFLAKE_COMPUTE_POOL: <your-compute-pool>"
echo "  SNOWFLAKE_ROLE: ${APP_CONSUMER_ROLE}"
echo ""
echo "To get the private key content for GitHub secret:"
echo "  cat $PROJECT_ROOT/keys/pipeline/snowflake_key.p8"
echo ""
echo "Next steps:"
echo "  1. Configure the GitHub secrets in your repository"
echo "  2. Run the 'Setup Package' workflow (manual) to create the app package and first version"
echo "  3. Run ./setup/create-application.sh --all-envs to create the application instances"
echo "  4. For subsequent updates, the QA/Stable pipelines will handle upgrades automatically"
echo ""
