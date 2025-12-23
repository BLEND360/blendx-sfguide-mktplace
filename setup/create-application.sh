#!/bin/bash

# Create Application Instance Script
# Run this AFTER:
#   1. provider-setup.sh (creates CI/CD user, roles, permissions)
#   2. First pipeline run (deploys the application package with a version)
#
# This script:
#   1. Creates the application instance from the deployed package
#   2. Grants required account-level permissions to the application
#   3. Optionally starts the application service

set -e  # Exit on error

# ============================================
# Load Shared Configuration
# ============================================

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "$SCRIPT_DIR/config.sh"

# ============================================
# Parse Arguments
# ============================================

ENV_SUFFIX=""
ALL_ENVS=false
ENVIRONMENTS=()

while [[ $# -gt 0 ]]; do
    case $1 in
        --env)
            ENVIRONMENTS+=("${2^^}")  # Convert to uppercase
            shift 2
            ;;
        --all-envs)
            ALL_ENVS=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--env <environment>] [--all-envs]"
            echo ""
            echo "Options:"
            echo "  --env <environment>  Environment suffix (e.g., qa, stable)"
            echo "                       This will append _QA or _STABLE to instance names"
            echo "                       Can be specified multiple times"
            echo "  --all-envs           Create both QA and STABLE environments"
            echo ""
            echo "Examples:"
            echo "  $0                   # Creates ${APP_INSTANCE_BASE}"
            echo "  $0 --env qa          # Creates ${APP_INSTANCE_BASE}_QA"
            echo "  $0 --env stable      # Creates ${APP_INSTANCE_BASE}_STABLE"
            echo "  $0 --all-envs        # Creates both _QA and _STABLE"
            echo "  $0 --env qa --env stable  # Same as --all-envs"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Handle --all-envs flag
if [ "$ALL_ENVS" = true ]; then
    ENVIRONMENTS=("QA" "STABLE")
fi

# If no environments specified, use empty string (default behavior)
if [ ${#ENVIRONMENTS[@]} -eq 0 ]; then
    ENVIRONMENTS=("")
fi

# ============================================
# Build list of instances to create
# ============================================

INSTANCES_TO_CREATE=()
for env in "${ENVIRONMENTS[@]}"; do
    if [ -n "$env" ]; then
        INSTANCES_TO_CREATE+=("${APP_INSTANCE_BASE}_${env}")
    else
        INSTANCES_TO_CREATE+=("${APP_INSTANCE_BASE}")
    fi
done

# ============================================
# Display Configuration
# ============================================

echo ""
echo "=========================================="
echo "Create Application Instance(s)"
echo "=========================================="
echo ""
echo "Configuration:"
echo "  Connection: $SNOW_CONNECTION"
echo "  CI/CD Role: $CICD_ROLE"
echo "  Consumer Role: $APP_CONSUMER_ROLE"
echo "  Package: $APP_PACKAGE_NAME"
echo "  Version: $APP_VERSION"
echo "  Compute Pool: $COMPUTE_POOL_NAME"
echo ""
echo "Instances to create:"
for instance in "${INSTANCES_TO_CREATE[@]}"; do
    echo "  - $instance"
done
echo ""

read -p "Continue with application creation? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Setup cancelled."
    exit 0
fi

# ============================================
# Step 1: Check Prerequisites
# ============================================

log_step "Step 1: Checking Prerequisites"

# Check if a version exists in the application package
echo -e "${BLUE}▶${NC} Checking for available versions in application package..."
VERSION_EXISTS=$(run_sql_silent "USE ROLE ${CICD_ROLE}; SHOW VERSIONS IN APPLICATION PACKAGE ${APP_PACKAGE_NAME};" | grep -i "| V" | wc -l | tr -d ' ' || echo "0")

if [ "$VERSION_EXISTS" -eq "0" ]; then
    log_error "No versions found in application package ${APP_PACKAGE_NAME}"
    echo ""
    echo "Please run the pipeline first to deploy a version, then run this script again."
    echo ""
    exit 1
fi

log_info "Version found in application package"

# ============================================
# Step 2: Get Latest Patch Number
# ============================================

log_step "Step 2: Getting Latest Patch Number"

echo -e "${BLUE}▶${NC} Querying latest patch for version ${APP_VERSION}..."
# Get versions output - format is pipe-separated table: | version | patch | label | ...
VERSIONS_OUTPUT=$(snow sql -q "USE ROLE ${CICD_ROLE}; SHOW VERSIONS IN APPLICATION PACKAGE ${APP_PACKAGE_NAME};" --connection ${SNOW_CONNECTION} 2>&1)

# Extract patch number from pipe-separated output
# Lines look like: | V1      | 2     | Version One | ...
LATEST_PATCH=$(echo "$VERSIONS_OUTPUT" | grep -i "| ${APP_VERSION} " | awk -F'|' '{print $3}' | tr -d ' ' | sort -n | tail -1 || echo "0")

# Ensure LATEST_PATCH is a valid number
if [ -z "$LATEST_PATCH" ] || ! [[ "$LATEST_PATCH" =~ ^[0-9]+$ ]]; then
    LATEST_PATCH=0
fi

log_info "Latest patch: ${LATEST_PATCH}"

# ============================================
# Function to create/upgrade application instance
# ============================================

create_application_instance() {
    local APP_INSTANCE_NAME=$1

    log_step "Creating Application Instance: ${APP_INSTANCE_NAME}"

    # Check if application exists using SELECT COUNT
    echo -e "${BLUE}▶${NC} Checking if application instance exists..."
    APP_EXISTS=$(snow sql -q "SELECT COUNT(*) FROM SNOWFLAKE.INFORMATION_SCHEMA.DATABASES WHERE DATABASE_NAME = '${APP_INSTANCE_NAME}' AND TYPE = 'APPLICATION';" --connection ${SNOW_CONNECTION} 2>/dev/null | grep -E "^\| *[0-9]+ *\|$" | tr -d '| ' || echo "0")

    # Ensure APP_EXISTS is a valid number
    if [ -z "$APP_EXISTS" ] || ! [[ "$APP_EXISTS" =~ ^[0-9]+$ ]]; then
        APP_EXISTS=0
    fi

    if [ "$APP_EXISTS" -gt "0" ]; then
        log_warning "Application instance already exists. Upgrading..."
        run_sql "Upgrading application" \
            "USE ROLE ${APP_CONSUMER_ROLE};
             ALTER APPLICATION ${APP_INSTANCE_NAME} UPGRADE USING VERSION ${APP_VERSION} PATCH ${LATEST_PATCH};"
    else
        log_info "Creating new application instance with version ${APP_VERSION} patch ${LATEST_PATCH}..."
        run_sql "Creating application instance" \
            "USE ROLE ${APP_CONSUMER_ROLE};
             CREATE APPLICATION ${APP_INSTANCE_NAME}
             FROM APPLICATION PACKAGE ${APP_PACKAGE_NAME}
             USING VERSION ${APP_VERSION} PATCH ${LATEST_PATCH}
             COMMENT = 'BlendX Native Application';"
    fi

    log_info "Application instance created/upgraded"

    # Grant Account-Level Permissions
    log_step "Granting Account-Level Permissions to ${APP_INSTANCE_NAME}"

    run_sql "Granting CREATE COMPUTE POOL to application" \
        "USE ROLE ACCOUNTADMIN;
         GRANT CREATE COMPUTE POOL ON ACCOUNT TO APPLICATION ${APP_INSTANCE_NAME};"

    run_sql "Granting BIND SERVICE ENDPOINT to application" \
        "USE ROLE ACCOUNTADMIN;
         GRANT BIND SERVICE ENDPOINT ON ACCOUNT TO APPLICATION ${APP_INSTANCE_NAME};"

    run_sql "Granting CREATE WAREHOUSE to application" \
        "USE ROLE ACCOUNTADMIN;
         GRANT CREATE WAREHOUSE ON ACCOUNT TO APPLICATION ${APP_INSTANCE_NAME};"

    run_sql "Granting CREATE EXTERNAL ACCESS INTEGRATION to application" \
        "USE ROLE ACCOUNTADMIN;
         GRANT CREATE EXTERNAL ACCESS INTEGRATION ON ACCOUNT TO APPLICATION ${APP_INSTANCE_NAME};"

    log_info "Account-level permissions granted to ${APP_INSTANCE_NAME}"
}

# ============================================
# Step 3: Create All Application Instances
# ============================================

for instance in "${INSTANCES_TO_CREATE[@]}"; do
    create_application_instance "$instance"
done

# ============================================
# Completion Message
# ============================================

echo ""
echo "=========================================="
echo -e "${GREEN}Application Instance(s) Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "Created applications:"
for instance in "${INSTANCES_TO_CREATE[@]}"; do
    echo "  - $instance"
done
echo ""
