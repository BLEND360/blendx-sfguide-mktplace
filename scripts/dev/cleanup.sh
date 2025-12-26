#!/bin/bash

# Cleanup Script for Snowflake Native App
# This script removes all resources created by provider-setup.sh and the pipelines
# Use this to clean up everything and start fresh
#
# Usage:
#   ./scripts/dev/cleanup.sh              # Interactive cleanup
#   ./scripts/dev/cleanup.sh --dry-run    # Show what would be deleted
#   ./scripts/dev/cleanup.sh --all        # Delete everything including infrastructure

set -e  # Exit on error

# ============================================
# Script Setup
# ============================================

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ============================================
# Configuration - Same as provider-setup.sh
# ============================================

SNOW_CONNECTION=${SNOW_CONNECTION:-"mkt_blendx_demo"}

# CI/CD User and Role
CICD_USER=${CICD_USER:-"MK_BLENDX_DEPLOY_USER"}
CICD_ROLE=${CICD_ROLE:-"MK_BLENDX_DEPLOY_ROLE"}

# Database objects
DATABASE_NAME=${DATABASE_NAME:-"BLENDX_APP"}
SCHEMA_NAME=${SCHEMA_NAME:-"NAPP"}
STAGE_NAME=${STAGE_NAME:-"APP_STAGE"}
IMAGE_REPO_NAME=${IMAGE_REPO_NAME:-"img_repo"}
WAREHOUSE_NAME=${WAREHOUSE_NAME:-"DEV_WH"}

# Application Package
APP_PACKAGE_NAME=${APP_PACKAGE_NAME:-"MK_BLENDX_APP_PKG"}

# Consumer role
APP_CONSUMER_ROLE=${APP_CONSUMER_ROLE:-"BLENDX_APP_ROLE"}

# Application Instance
APP_INSTANCE_NAME=${APP_INSTANCE_NAME:-"BLENDX_APP_INSTANCE"}

# Compute Pool
COMPUTE_POOL_NAME=${COMPUTE_POOL_NAME:-"BLENDX_CP"}

# Options
DRY_RUN=false
CLEAN_ALL=false

# Load .env file if it exists
if [ -f "$SCRIPT_DIR/.env" ]; then
    echo -e "${BLUE}Loading configuration from .env file...${NC}"
    source "$SCRIPT_DIR/.env"
fi

# ============================================
# Parse Command Line Arguments
# ============================================

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --all)
            CLEAN_ALL=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --dry-run    Show what would be deleted without making changes"
            echo "  --all        Delete everything including database infrastructure and CI/CD user/role"
            echo "  --help       Show this help message"
            echo ""
            echo "Environment Variables (can also be set in .env file):"
            echo "  SNOW_CONNECTION      Snowflake connection name (default: mkt_blendx_demo)"
            echo "  CICD_USER            CI/CD user name (default: MK_BLENDX_DEPLOY_USER)"
            echo "  CICD_ROLE            CI/CD role name (default: MK_BLENDX_DEPLOY_ROLE)"
            echo "  DATABASE_NAME        Database name (default: BLENDX_APP)"
            echo "  SCHEMA_NAME          Schema name (default: NAPP)"
            echo "  APP_PACKAGE_NAME     Application package name (default: MK_BLENDX_APP_PKG)"
            echo "  APP_INSTANCE_NAME    Application instance name (default: BLENDX_APP_INSTANCE)"
            echo "  APP_CONSUMER_ROLE    Consumer role name (default: BLENDX_APP_ROLE)"
            echo "  COMPUTE_POOL_NAME    Compute pool name (default: BLENDX_CP)"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

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

    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}[DRY RUN]${NC} ${BLUE}▶${NC} $description"
        echo -e "  ${YELLOW}Would execute:${NC} $sql"
    else
        echo -e "${BLUE}▶${NC} $description"
        snow sql -q "$sql" --connection ${SNOW_CONNECTION} 2>/dev/null || true
    fi
}

# ============================================
# Display Configuration
# ============================================

echo ""
echo "==========================================="
echo "Snowflake Native App Cleanup"
echo "==========================================="
echo ""
echo "Configuration:"
echo "  Connection:      $SNOW_CONNECTION"
echo "  CI/CD User:      $CICD_USER"
echo "  CI/CD Role:      $CICD_ROLE"
echo "  Consumer Role:   $APP_CONSUMER_ROLE"
echo "  Database:        $DATABASE_NAME"
echo "  Schema:          $SCHEMA_NAME"
echo "  Package:         $APP_PACKAGE_NAME"
echo "  Instance:        $APP_INSTANCE_NAME"
echo "  Compute Pool:    $COMPUTE_POOL_NAME"
echo ""
echo "  Dry Run:         $DRY_RUN"
echo "  Clean All:       $CLEAN_ALL"
echo ""

if [ "$DRY_RUN" = false ]; then
    log_warning "This will DELETE resources from your Snowflake account!"
    echo ""
    read -p "Are you sure you want to continue? (yes/no): " confirmation
    if [ "$confirmation" != "yes" ]; then
        echo "Cleanup cancelled."
        exit 0
    fi
fi

# ============================================
# Step 1: Drop Service (if running inside app)
# ============================================

log_step "Step 1: Stop Services"

run_sql "Stopping service in application (if exists)" \
    "USE ROLE ${APP_CONSUMER_ROLE};
     CALL ${APP_INSTANCE_NAME}.app_public.service_stop();" || true

log_info "Service stop attempted"

# ============================================
# Step 2: Drop Application Instance
# ============================================

log_step "Step 2: Drop Application Instance"

run_sql "Dropping application instance" \
    "USE ROLE ${APP_CONSUMER_ROLE};
     DROP APPLICATION IF EXISTS ${APP_INSTANCE_NAME} CASCADE;"

log_info "Application instance dropped (if existed)"

# ============================================
# Step 3: Drop Compute Pool
# ============================================

log_step "Step 3: Drop Compute Pool"

run_sql "Dropping compute pool" \
    "USE ROLE ${APP_CONSUMER_ROLE};
     DROP COMPUTE POOL IF EXISTS ${COMPUTE_POOL_NAME};"

log_info "Compute pool dropped (if existed)"

# ============================================
# Step 4: Drop Application Package
# ============================================

log_step "Step 4: Drop Application Package"

run_sql "Dropping application package" \
    "USE ROLE ${CICD_ROLE};
     DROP APPLICATION PACKAGE IF EXISTS ${APP_PACKAGE_NAME};"

log_info "Application package dropped (if existed)"

# ============================================
# Step 5: Clean Stage Contents
# ============================================

log_step "Step 5: Clean Stage Contents"

run_sql "Removing files from stage" \
    "USE ROLE ${CICD_ROLE};
     REMOVE @${DATABASE_NAME}.${SCHEMA_NAME}.${STAGE_NAME};"

log_info "Stage contents removed (if existed)"

# ============================================
# Step 6: Clean Infrastructure (Optional)
# ============================================

if [ "$CLEAN_ALL" = true ]; then
    log_step "Step 6: Clean Infrastructure (--all flag)"

    if [ "$DRY_RUN" = false ]; then
        log_warning "This will delete the database, CI/CD user, and roles!"
        read -p "Are you ABSOLUTELY sure? (yes/no): " infra_confirmation
        if [ "$infra_confirmation" != "yes" ]; then
            log_warning "Skipping infrastructure cleanup"
            CLEAN_ALL=false
        fi
    fi

    if [ "$CLEAN_ALL" = true ]; then
        # Drop database (includes schema, stage, image repo)
        run_sql "Dropping database (includes schema, stage, image repo)" \
            "USE ROLE ACCOUNTADMIN;
             DROP DATABASE IF EXISTS ${DATABASE_NAME};"

        # Drop CI/CD user
        run_sql "Dropping CI/CD user" \
            "USE ROLE ACCOUNTADMIN;
             DROP USER IF EXISTS ${CICD_USER};"

        # Drop CI/CD role
        run_sql "Dropping CI/CD role" \
            "USE ROLE ACCOUNTADMIN;
             DROP ROLE IF EXISTS ${CICD_ROLE};"

        # Drop Consumer role
        run_sql "Dropping Consumer role" \
            "USE ROLE ACCOUNTADMIN;
             DROP ROLE IF EXISTS ${APP_CONSUMER_ROLE};"

        log_info "Infrastructure cleaned"
    fi
else
    echo ""
    log_info "Skipping infrastructure cleanup (use --all to include database, user, and roles)"
fi

# ============================================
# Completion Message
# ============================================

echo ""
echo "==========================================="
if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}Dry Run Complete!${NC}"
    echo "==========================================="
    echo ""
    echo "No changes were made. Run without --dry-run to execute cleanup."
else
    echo -e "${GREEN}Cleanup Complete!${NC}"
    echo "==========================================="
    echo ""
    echo "Resources removed:"
    echo "  - Application instance: ${APP_INSTANCE_NAME}"
    echo "  - Compute pool: ${COMPUTE_POOL_NAME}"
    echo "  - Application package: ${APP_PACKAGE_NAME}"
    echo "  - Stage contents: ${DATABASE_NAME}.${SCHEMA_NAME}.${STAGE_NAME}"
    if [ "$CLEAN_ALL" = true ]; then
        echo "  - Database: ${DATABASE_NAME}"
        echo "  - CI/CD User: ${CICD_USER}"
        echo "  - CI/CD Role: ${CICD_ROLE}"
        echo "  - Consumer Role: ${APP_CONSUMER_ROLE}"
    fi
    echo ""
    echo "Next steps to redeploy from scratch:"
    echo ""
    if [ "$CLEAN_ALL" = true ]; then
        echo "  1. Run provider setup:"
        echo -e "     ${CYAN}./setup/provider-setup.sh${NC}"
        echo ""
        echo "  2. Configure GitHub secrets/variables"
        echo ""
        echo "  3. Run create-major-version pipeline (manual trigger)"
        echo ""
        echo "  4. Run deploy-qa pipeline (merge to qa branch)"
        echo ""
        echo "  5. Create application instance:"
        echo -e "     ${CYAN}./setup/create-application.sh${NC}"
    else
        echo "  1. Run create-major-version pipeline (manual trigger)"
        echo ""
        echo "  2. Run deploy-qa pipeline (merge to qa branch)"
        echo ""
        echo "  3. Create application instance:"
        echo -e "     ${CYAN}./setup/create-application.sh${NC}"
    fi
fi
echo ""
