#!/bin/bash

# Release script for Snowflake Native App Marketplace
# This script promotes a version from QA channel to DEFAULT (or specified channel)
# By default, it reads the current version/patch from QA and promotes it
# Usage: ./release.sh [--dry-run] [--version VERSION] [--patch PATCH] [--channel CHANNEL]

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
APP_VERSION=""  # Will be auto-detected from QA channel if not specified
APP_PATCH=""    # Will be auto-detected from QA channel if not specified
SOURCE_CHANNEL=${SOURCE_CHANNEL:-"QA"}
RELEASE_CHANNEL=${RELEASE_CHANNEL:-"DEFAULT"}
DRY_RUN=false
SUBMIT_REVIEW=false
LIST_ONLY=false
VERSION_SPECIFIED=false
PATCH_SPECIFIED=false

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
            VERSION_SPECIFIED=true
            shift 2
            ;;
        --patch|-p)
            APP_PATCH="$2"
            PATCH_SPECIFIED=true
            shift 2
            ;;
        --from|--source)
            SOURCE_CHANNEL="$2"
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
        --channel|-c)
            RELEASE_CHANNEL="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Release script for Snowflake Native App Marketplace"
            echo "Promotes a version from QA channel to DEFAULT (production) channel."
            echo ""
            echo "By default, this script reads the current version/patch from the QA channel"
            echo "and promotes it to the DEFAULT channel for marketplace distribution."
            echo ""
            echo "Options:"
            echo "  --dry-run           Show what would be done without making changes"
            echo "  --version, -v VER   Specify version to release (default: auto-detect from QA)"
            echo "  --patch, -p NUM     Specify patch number (default: auto-detect from QA)"
            echo "  --from, --source CH Source channel to read version from (default: QA)"
            echo "  --channel, -c NAME  Target release channel (default: DEFAULT)"
            echo "  --submit-review     Show instructions for security review submission"
            echo "  --list              List all versions and their release status"
            echo "  --help, -h          Show this help message"
            echo ""
            echo "Release Channels:"
            echo "  DEFAULT  - Production channel for marketplace listing"
            echo "  QA       - Internal testing, versions never reviewed by Snowflake"
            echo "  ALPHA    - For external testing"
            echo ""
            echo "Examples:"
            echo "  $0                               # Promote QA version to DEFAULT"
            echo "  $0 --list                        # List all versions and their status"
            echo "  $0 --channel ALPHA               # Promote QA version to ALPHA"
            echo "  $0 --version v1 --patch 5        # Release specific version/patch to DEFAULT"
            echo "  $0 --dry-run                     # Dry run (show what would be done)"
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
# List Versions Mode (before other processing)
# ============================================

if [ "$LIST_ONLY" = true ]; then
    echo ""
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
# Auto-detect Version/Patch from Source Channel
# ============================================

echo ""
echo "=========================================="
echo "[1/5] Reading current version from ${SOURCE_CHANNEL} channel..."
echo "=========================================="

if [ "$DRY_RUN" = false ]; then
    # Get release directives to find current QA version/patch
    TEMP_DIRECTIVES=$(mktemp)
    snow sql -q "USE ROLE ${APP_PACKAGE_ROLE}; SHOW RELEASE DIRECTIVES IN APPLICATION PACKAGE ${APP_PACKAGE_NAME};" --connection ${SNOW_CONNECTION} > "$TEMP_DIRECTIVES" 2>&1 || true

    # Extract version and patch from the source channel (format: | CHANNEL | ... | VERSION | PATCH | ...)
    # The output format is: | name | ... | version | patch | ...
    SOURCE_LINE=$(cat "$TEMP_DIRECTIVES" | grep -i "| ${SOURCE_CHANNEL} " | head -1)

    if [ -z "$SOURCE_LINE" ]; then
        echo -e "${RED}Error: No release directive found for ${SOURCE_CHANNEL} channel${NC}"
        echo ""
        echo "Available release directives:"
        cat "$TEMP_DIRECTIVES"
        rm -f "$TEMP_DIRECTIVES"
        echo ""
        echo "Run deploy.sh first to create a version in the ${SOURCE_CHANNEL} channel."
        exit 1
    fi

    # Parse version and patch from the line
    # Format: | channel | target_type | ... | version | patch | ...
    if [ "$VERSION_SPECIFIED" = false ]; then
        DETECTED_VERSION=$(echo "$SOURCE_LINE" | awk -F'|' '{for(i=1;i<=NF;i++) if($i ~ /v[0-9]/) print $i}' | tr -d ' ' | head -1)
        if [ -n "$DETECTED_VERSION" ]; then
            APP_VERSION="$DETECTED_VERSION"
            echo -e "${GREEN}✓ Auto-detected version from ${SOURCE_CHANNEL}: ${APP_VERSION}${NC}"
        fi
    else
        echo -e "${CYAN}Using specified version: ${APP_VERSION}${NC}"
    fi

    if [ "$PATCH_SPECIFIED" = false ]; then
        # Get patch number - it's typically after the version column
        DETECTED_PATCH=$(echo "$SOURCE_LINE" | awk -F'|' '{for(i=1;i<=NF;i++) if($i ~ /^[[:space:]]*[0-9]+[[:space:]]*$/ && $(i-1) ~ /v[0-9]/) print $i}' | tr -d ' ' | head -1)
        if [ -n "$DETECTED_PATCH" ] && [[ "$DETECTED_PATCH" =~ ^[0-9]+$ ]]; then
            APP_PATCH="$DETECTED_PATCH"
            echo -e "${GREEN}✓ Auto-detected patch from ${SOURCE_CHANNEL}: ${APP_PATCH}${NC}"
        fi
    else
        echo -e "${CYAN}Using specified patch: ${APP_PATCH}${NC}"
    fi

    rm -f "$TEMP_DIRECTIVES"

    # Fallback: if version still not set, try to get it from versions list
    if [ -z "$APP_VERSION" ]; then
        echo -e "${YELLOW}Could not detect version from release directive, checking versions...${NC}"
        TEMP_VERSIONS=$(mktemp)
        snow sql -q "USE ROLE ${APP_PACKAGE_ROLE}; SHOW VERSIONS IN APPLICATION PACKAGE ${APP_PACKAGE_NAME};" --connection ${SNOW_CONNECTION} > "$TEMP_VERSIONS" 2>&1 || true
        APP_VERSION=$(cat "$TEMP_VERSIONS" | grep -i "| v" | head -1 | awk -F'|' '{print $2}' | tr -d ' ')
        rm -f "$TEMP_VERSIONS"

        if [ -z "$APP_VERSION" ]; then
            echo -e "${RED}Error: Could not determine version. Please specify with --version${NC}"
            exit 1
        fi
        echo -e "${GREEN}✓ Found version: ${APP_VERSION}${NC}"
    fi

    # Fallback: if patch still not set, get latest patch for the version
    if [ -z "$APP_PATCH" ]; then
        echo -e "${YELLOW}Could not detect patch from release directive, getting latest...${NC}"
        TEMP_VERSIONS=$(mktemp)
        snow sql -q "USE ROLE ${APP_PACKAGE_ROLE}; SHOW VERSIONS IN APPLICATION PACKAGE ${APP_PACKAGE_NAME};" --connection ${SNOW_CONNECTION} > "$TEMP_VERSIONS" 2>&1 || true
        APP_PATCH=$(cat "$TEMP_VERSIONS" | grep -i "| ${APP_VERSION} " | awk -F'|' '{print $3}' | tr -d ' ' | sort -n | tail -1)
        rm -f "$TEMP_VERSIONS"

        if [ -z "$APP_PATCH" ] || ! [[ "$APP_PATCH" =~ ^[0-9]+$ ]]; then
            APP_PATCH=0
        fi
        echo -e "${GREEN}✓ Latest patch for ${APP_VERSION}: ${APP_PATCH}${NC}"
    fi
else
    if [ -z "$APP_VERSION" ]; then
        APP_VERSION="v1"  # Default for dry run
    fi
    if [ -z "$APP_PATCH" ]; then
        APP_PATCH=0  # Default for dry run
    fi
    echo "[DRY RUN] Would read version/patch from ${SOURCE_CHANNEL} channel"
fi

echo ""

# ============================================
# Display Configuration
# ============================================

echo "=========================================="
echo "Snowflake Native App Release Management"
echo "=========================================="
echo ""
echo "Configuration:"
echo "  Connection: $SNOW_CONNECTION"
echo "  Role: $APP_PACKAGE_ROLE"
echo "  Package: $APP_PACKAGE_NAME"
echo "  Source Channel: $SOURCE_CHANNEL"
echo "  Target Channel: $RELEASE_CHANNEL"
echo "  Version: $APP_VERSION"
echo "  Patch: $APP_PATCH"
echo ""

# ============================================
# Verify Version Exists
# ============================================

echo "=========================================="
echo "[2/5] Verifying version ${APP_VERSION} patch ${APP_PATCH} exists..."
echo "=========================================="

if [ "$DRY_RUN" = false ]; then
    VERSION_EXISTS=$(snow sql -q "USE ROLE ${APP_PACKAGE_ROLE}; SHOW VERSIONS IN APPLICATION PACKAGE ${APP_PACKAGE_NAME};" --connection ${SNOW_CONNECTION} 2>&1 | grep -i "| ${APP_VERSION} " | grep -E "\|\s*${APP_PATCH}\s*\|" | wc -l | tr -d ' ')

    if [ -z "$VERSION_EXISTS" ] || [ "$VERSION_EXISTS" -eq "0" ]; then
        echo -e "${YELLOW}Warning: Exact patch ${APP_PATCH} not found, checking if version exists...${NC}"
        VERSION_EXISTS=$(snow sql -q "USE ROLE ${APP_PACKAGE_ROLE}; SHOW VERSIONS IN APPLICATION PACKAGE ${APP_PACKAGE_NAME};" --connection ${SNOW_CONNECTION} 2>&1 | grep -i "| ${APP_VERSION} " | wc -l | tr -d ' ')

        if [ -z "$VERSION_EXISTS" ] || [ "$VERSION_EXISTS" -eq "0" ]; then
            echo -e "${RED}Error: Version ${APP_VERSION} does not exist in package ${APP_PACKAGE_NAME}${NC}"
            echo ""
            echo "Available versions:"
            snow sql -q "USE ROLE ${APP_PACKAGE_ROLE}; SHOW VERSIONS IN APPLICATION PACKAGE ${APP_PACKAGE_NAME};" --connection ${SNOW_CONNECTION}
            echo ""
            echo "Run deploy.sh first to register the version."
            exit 1
        fi
    fi
    echo -e "${GREEN}✓ Version ${APP_VERSION} patch ${APP_PATCH} exists${NC}"
fi
echo ""

# ============================================
# Add Version to Release Channel
# ============================================

echo "=========================================="
echo "[3/5] Adding ${APP_VERSION} to ${RELEASE_CHANNEL} release channel..."
echo "=========================================="

run_sql "Adding version to ${RELEASE_CHANNEL} release channel" \
    "ALTER APPLICATION PACKAGE ${APP_PACKAGE_NAME} MODIFY RELEASE CHANNEL ${RELEASE_CHANNEL} ADD VERSION ${APP_VERSION};" || echo "Version may already be in channel (OK)"

echo ""

# ============================================
# Set Release Directive
# ============================================

echo "=========================================="
echo "[4/5] Setting release directive to ${APP_VERSION} patch ${APP_PATCH}..."
echo "=========================================="

run_sql "Setting ${RELEASE_CHANNEL} release directive" \
    "ALTER APPLICATION PACKAGE ${APP_PACKAGE_NAME} MODIFY RELEASE CHANNEL ${RELEASE_CHANNEL} SET DEFAULT RELEASE DIRECTIVE VERSION=${APP_VERSION} PATCH=${APP_PATCH};"

echo ""

# ============================================
# Submit for Security Review (if requested)
# ============================================

echo "=========================================="
echo "[5/5] Security Review Status..."
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
