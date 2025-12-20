#!/bin/bash

# Cleanup Script for Snowflake Native App
# This script removes all resources created during deployment
# Use this to clean up after failed deployments or to start fresh

set -e  # Exit on error

# ============================================
# Script Setup
# ============================================

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ============================================
# Load Configuration
# ============================================

SNOW_CONNECTION=${SNOW_CONNECTION:-"mkt_blendx_demo"}
APP_PROVIDER_ROLE=${APP_PROVIDER_ROLE:-"naspcs_role"}
APP_CONSUMER_ROLE=${APP_CONSUMER_ROLE:-"nac_test"}
APP_PACKAGE_NAME=${APP_PACKAGE_NAME:-"spcs_app_pkg_test"}
APP_INSTANCE_NAME=${APP_INSTANCE_NAME:-"spcs_app_instance_test"}
COMPUTE_POOL=${COMPUTE_POOL:-"pool_nac"}
SECRET_DATABASE=${SECRET_DATABASE:-"secrets_db"}
DRY_RUN=false
CLEAN_SECRETS=false

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
        --clean-secrets)
            CLEAN_SECRETS=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --dry-run          Show what would be deleted without making changes"
            echo "  --clean-secrets    Also delete the secrets database (WARNING: destructive)"
            echo "  --help             Show this help message"
            echo ""
            echo "Environment Variables (can also be set in .env file):"
            echo "  SNOW_CONNECTION    Snowflake connection name (default: mkt_blendx_demo)"
            echo "  APP_PROVIDER_ROLE  Provider role (default: naspcs_role)"
            echo "  APP_CONSUMER_ROLE  Consumer role (default: nac_test)"
            echo "  APP_PACKAGE_NAME   Application package name (default: spcs_app_pkg_test)"
            echo "  APP_INSTANCE_NAME  Application instance name (default: spcs_app_instance_test)"
            echo "  COMPUTE_POOL       Compute pool name (default: pool_nac)"
            echo "  SECRET_DATABASE    Secret database name (default: secrets_db)"
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
        echo -e "${YELLOW}Would execute:${NC} $sql"
    else
        echo -e "${BLUE}▶${NC} $description"
        snow sql -q "$sql" --connection ${SNOW_CONNECTION} || true
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
echo "  Connection: $SNOW_CONNECTION"
echo "  Provider Role: $APP_PROVIDER_ROLE"
echo "  Consumer Role: $APP_CONSUMER_ROLE"
echo "  Package: $APP_PACKAGE_NAME"
echo "  Instance: $APP_INSTANCE_NAME"
echo "  Compute Pool: $COMPUTE_POOL"
echo "  Secret Database: $SECRET_DATABASE"
echo "  Dry Run: $DRY_RUN"
echo "  Clean Secrets: $CLEAN_SECRETS"
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
# Step 1: Stop and Drop Service
# ============================================

log_step "Step 1: Stop and Drop Service"

run_sql "Stopping service" \
    "USE ROLE ${APP_CONSUMER_ROLE};
     USE APPLICATION ${APP_INSTANCE_NAME};
     DROP SERVICE IF EXISTS app_public.blendx_st_spcs;"

log_info "Service dropped (if it existed)"

# ============================================
# Step 2: Drop Application Instance
# ============================================

log_step "Step 2: Drop Application Instance"

run_sql "Dropping application instance" \
    "USE ROLE ${APP_CONSUMER_ROLE};
     DROP APPLICATION IF EXISTS ${APP_INSTANCE_NAME} CASCADE;"

log_info "Application instance dropped (if it existed)"

# ============================================
# Step 3: Drop Compute Pool
# ============================================

log_step "Step 3: Drop Compute Pool"

run_sql "Dropping compute pool" \
    "USE ROLE ${APP_CONSUMER_ROLE};
     DROP COMPUTE POOL IF EXISTS ${COMPUTE_POOL};"

log_info "Compute pool dropped (if they existed)"

# ============================================
# Step 4: Drop Application Package
# ============================================

log_step "Step 4: Drop Application Package"

run_sql "Dropping application package" \
    "USE ROLE ${APP_PROVIDER_ROLE};
     DROP APPLICATION PACKAGE IF EXISTS ${APP_PACKAGE_NAME};"

log_info "Application package dropped (if it existed)"

# ============================================
# Step 5: Clean Secrets (Optional)
# ============================================

if [ "$CLEAN_SECRETS" = true ]; then
    log_step "Step 5: Clean Secrets Database"

    log_warning "This will delete the secrets database and all secrets in it!"

    if [ "$DRY_RUN" = false ]; then
        read -p "Are you ABSOLUTELY sure you want to delete secrets? (yes/no): " secret_confirmation
        if [ "$secret_confirmation" != "yes" ]; then
            log_warning "Skipping secrets cleanup"
        else
            run_sql "Dropping secrets database" \
                "USE ROLE ${APP_CONSUMER_ROLE};
                 DROP DATABASE IF EXISTS ${SECRET_DATABASE};"

            log_info "Secrets database dropped"
        fi
    else
        echo -e "${YELLOW}[DRY RUN]${NC} Would drop secrets database: ${SECRET_DATABASE}"
    fi
else
    echo ""
    log_info "Skipping secrets cleanup (use --clean-secrets to include)"
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
    echo "All resources have been removed."
    echo ""
    echo "Next steps:"
    echo ""
    echo "1. Run complete setup to redeploy:"
    echo -e "   ${CYAN}./scripts/provider-setup.sh${NC}"
    echo ""
    echo "2. Or manually recreate resources as needed"
fi
echo ""
