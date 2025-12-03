#!/bin/bash

# Release script for Snowflake Native App Marketplace
# This script handles the release process for publishing versions to external accounts
# Usage: ./release.sh [--dry-run] [--version VERSION] [--submit-review]

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
# Load Configuration
# ============================================

SNOW_CONNECTION=${SNOW_CONNECTION:-"mkt_blendx_demo"}
APP_PACKAGE_ROLE=${APP_PACKAGE_ROLE:-"naspcs_role"}
APP_PACKAGE_NAME=${APP_PACKAGE_NAME:-"spcs_app_pkg_test"}
APP_VERSION=${APP_VERSION:-"v6"}
DRY_RUN=false
SUBMIT_REVIEW=false
LIST_ONLY=false

# Load .env file if it exists
if [ -f "$SCRIPT_DIR/.env" ]; then
    echo -e "${BLUE}Loading configuration from .env file...${NC}"
    source "$SCRIPT_DIR/.env"
fi

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            echo -e "${YELLOW}Running in DRY RUN mode - no changes will be made${NC}"
            shift
            ;;
        --version|-v)
            APP_VERSION="$2"
            shift 2
            ;;
        --submit-review)
            SUBMIT_REVIEW=true
            shift
            ;;
        --list)
            LIST_ONLY=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Release script for Snowflake Native App Marketplace"
            echo ""
            echo "Options:"
            echo "  --dry-run           Show what would be done without making changes"
            echo "  --version, -v VER   Specify version to release (default: ${APP_VERSION})"
            echo "  --submit-review     Submit the version for security review (required for external release)"
            echo "  --list              List all versions and their release status"
            echo "  --help, -h          Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 --list                        # List all versions and their status"
            echo "  $0 --version V4 --submit-review  # Submit V4 for marketplace review"
            echo "  $0 --dry-run --version V5        # Dry run for V5 release"
            echo ""
            echo "Configuration can be set via .env file in the scripts/ directory."
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# ============================================
# Helper Functions
# ============================================

run_command() {
    local description=$1
    local command=$2

    if [ "$DRY_RUN" = true ]; then
        echo -e "${BLUE}[DRY RUN]${NC} $description"
        echo -e "${YELLOW}  Command: $command${NC}"
    else
        echo -e "${GREEN}▶${NC} $description"
        eval "$command"
    fi
}

run_sql() {
    local description=$1
    local sql=$2

    if [ "$DRY_RUN" = true ]; then
        echo -e "${BLUE}[DRY RUN]${NC} $description"
        echo -e "${YELLOW}  SQL: $sql${NC}"
    else
        echo -e "${GREEN}▶${NC} $description"
        snow sql -q "USE ROLE ${APP_PACKAGE_ROLE}; $sql" --connection ${SNOW_CONNECTION}
    fi
}

# ============================================
# Display Configuration
# ============================================

echo ""
echo "=========================================="
echo "Snowflake Native App Release Management"
echo "=========================================="
echo ""
echo "Configuration:"
echo "  Connection: $SNOW_CONNECTION"
echo "  Role: $APP_PACKAGE_ROLE"
echo "  Package: $APP_PACKAGE_NAME"
echo "  Version: $APP_VERSION"
echo ""

# ============================================
# List Versions Mode
# ============================================

if [ "$LIST_ONLY" = true ]; then
    echo "=========================================="
    echo "Listing all versions and release status..."
    echo "=========================================="
    echo ""

    echo -e "${CYAN}=== Application Package Versions ===${NC}"
    snow sql -q "USE ROLE ${APP_PACKAGE_ROLE}; SHOW VERSIONS IN APPLICATION PACKAGE ${APP_PACKAGE_NAME};" --connection ${SNOW_CONNECTION}

    echo ""
    echo -e "${CYAN}=== Release Channels ===${NC}"
    snow sql -q "USE ROLE ${APP_PACKAGE_ROLE}; SHOW RELEASE CHANNELS IN APPLICATION PACKAGE ${APP_PACKAGE_NAME};" --connection ${SNOW_CONNECTION}

    echo ""
    echo -e "${CYAN}=== Release Directives ===${NC}"
    snow sql -q "USE ROLE ${APP_PACKAGE_ROLE}; SHOW RELEASE DIRECTIVES IN APPLICATION PACKAGE ${APP_PACKAGE_NAME};" --connection ${SNOW_CONNECTION}

    echo ""
    echo -e "${CYAN}=== Listing Status ===${NC}"
    snow sql -q "USE ROLE ${APP_PACKAGE_ROLE}; DESCRIBE APPLICATION PACKAGE ${APP_PACKAGE_NAME};" --connection ${SNOW_CONNECTION}

    exit 0
fi

# ============================================
# Check Version Exists
# ============================================

echo "=========================================="
echo "[1/4] Checking version ${APP_VERSION} exists..."
echo "=========================================="

if [ "$DRY_RUN" = false ]; then
    VERSION_EXISTS=$(snow sql -q "USE ROLE ${APP_PACKAGE_ROLE}; SHOW VERSIONS IN APPLICATION PACKAGE ${APP_PACKAGE_NAME};" --connection ${SNOW_CONNECTION} 2>&1 | grep -i "${APP_VERSION}" | wc -l | tr -d ' ')

    if [ "$VERSION_EXISTS" -eq "0" ]; then
        echo -e "${RED}Error: Version ${APP_VERSION} does not exist in package ${APP_PACKAGE_NAME}${NC}"
        echo ""
        echo "Available versions:"
        snow sql -q "USE ROLE ${APP_PACKAGE_ROLE}; SHOW VERSIONS IN APPLICATION PACKAGE ${APP_PACKAGE_NAME};" --connection ${SNOW_CONNECTION}
        echo ""
        echo "Run deploy.sh first to register the version."
        exit 1
    fi
    echo -e "${GREEN}✓ Version ${APP_VERSION} exists${NC}"
fi
echo ""

# ============================================
# Add Version to Release Channel
# ============================================

echo "=========================================="
echo "[2/4] Adding ${APP_VERSION} to DEFAULT release channel..."
echo "=========================================="

run_sql "Adding version to DEFAULT release channel" \
    "ALTER APPLICATION PACKAGE ${APP_PACKAGE_NAME} MODIFY RELEASE CHANNEL DEFAULT ADD VERSION ${APP_VERSION};" || echo "Version may already be in channel (OK)"

echo ""

# ============================================
# Set Release Directive
# ============================================

echo "=========================================="
echo "[3/4] Setting release directive..."
echo "=========================================="

run_sql "Setting DEFAULT release directive" \
    "ALTER APPLICATION PACKAGE ${APP_PACKAGE_NAME} MODIFY RELEASE CHANNEL DEFAULT SET DEFAULT RELEASE DIRECTIVE VERSION=${APP_VERSION} PATCH=0;"

echo ""

# ============================================
# Submit for Security Review (if requested)
# ============================================

echo "=========================================="
echo "[4/4] Security Review Status..."
echo "=========================================="

if [ "$SUBMIT_REVIEW" = true ]; then
    echo -e "${YELLOW}Note: Security review submission is done through Snowflake Provider Studio UI${NC}"
    echo ""
    echo "To submit for review:"
    echo "  1. Go to Snowflake Provider Studio (https://app.snowflake.com)"
    echo "  2. Navigate to Provider Studio > Listings"
    echo "  3. Select your listing"
    echo "  4. Go to 'Releases' tab"
    echo "  5. Click 'Submit for Review' for version ${APP_VERSION}"
    echo ""
    echo -e "${CYAN}The review process typically takes 1-3 business days.${NC}"
else
    echo "Security review not requested."
    echo ""
    echo -e "${YELLOW}Important:${NC} Before the version can be released to external accounts,"
    echo "it must pass Snowflake's security review process."
    echo ""
    echo "Use --submit-review flag to see instructions for submitting."
fi

echo ""

# ============================================
# Show Current Status
# ============================================

echo "=========================================="
echo "Current Release Status"
echo "=========================================="

if [ "$DRY_RUN" = false ]; then
    echo ""
    echo -e "${CYAN}Versions:${NC}"
    snow sql -q "USE ROLE ${APP_PACKAGE_ROLE}; SHOW VERSIONS IN APPLICATION PACKAGE ${APP_PACKAGE_NAME};" --connection ${SNOW_CONNECTION}

    echo ""
    echo -e "${CYAN}Release Directives:${NC}"
    snow sql -q "USE ROLE ${APP_PACKAGE_ROLE}; SHOW RELEASE DIRECTIVES IN APPLICATION PACKAGE ${APP_PACKAGE_NAME};" --connection ${SNOW_CONNECTION}
fi

# ============================================
# Completion Message
# ============================================

echo ""
echo "=========================================="
if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}DRY RUN completed!${NC}"
    echo "No changes were made. Run without --dry-run to apply."
else
    echo -e "${GREEN}Release configuration completed!${NC}"
fi
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "  1. If not yet done, submit for security review in Provider Studio"
echo "  2. Wait for Snowflake to approve the version (1-3 business days)"
echo "  3. Once approved, the version will be available to external accounts"
echo ""
echo "Useful commands:"
echo ""
echo "  List all versions:"
echo "    $0 --list"
echo ""
echo "  Check release status in Provider Studio:"
echo "    https://app.snowflake.com > Provider Studio > Listings"
echo ""
