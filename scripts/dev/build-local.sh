#!/bin/bash
# =============================================================================
# Build Docker images locally for development
# =============================================================================
# This script generates requirements.txt and builds the Docker images locally.
# Use this for local development and testing before pushing to CI.
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Default values
BUILD_BACKEND=true
BUILD_FRONTEND=false
BUILD_ROUTER=false
BUILD_ALL=false
TAG="latest"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --backend)
            BUILD_BACKEND=true
            shift
            ;;
        --frontend)
            BUILD_FRONTEND=true
            shift
            ;;
        --router)
            BUILD_ROUTER=true
            shift
            ;;
        --all)
            BUILD_ALL=true
            shift
            ;;
        --tag)
            TAG="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Build Docker images locally for development."
            echo ""
            echo "Options:"
            echo "  --backend     Build backend image (default)"
            echo "  --frontend    Build frontend image"
            echo "  --router      Build router image"
            echo "  --all         Build all images"
            echo "  --tag TAG     Docker image tag (default: latest)"
            echo "  -h, --help    Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                    # Build backend only"
            echo "  $0 --all              # Build all images"
            echo "  $0 --backend --tag v1 # Build backend with tag v1"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

if [ "$BUILD_ALL" = true ]; then
    BUILD_BACKEND=true
    BUILD_FRONTEND=true
    BUILD_ROUTER=true
fi

cd "$PROJECT_ROOT"

# Build backend
if [ "$BUILD_BACKEND" = true ]; then
    echo "=============================================="
    echo "Building backend image..."
    echo "=============================================="

    # Check if uv is installed
    if ! command -v uv &> /dev/null; then
        echo "Error: uv is not installed."
        echo "Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi

    # Generate requirements.txt
    echo "Generating requirements.txt from pyproject.toml..."
    cd backend
    uv export --no-hashes --no-dev -o requirements.txt
    echo "Generated requirements.txt with $(wc -l < requirements.txt | tr -d ' ') lines"

    # Build image
    cd "$PROJECT_ROOT"
    docker build \
        --platform linux/amd64 \
        -t eap_backend:$TAG \
        ./backend

    echo "✓ Backend image built: eap_backend:$TAG"
    echo ""
fi

# Build frontend
if [ "$BUILD_FRONTEND" = true ]; then
    echo "=============================================="
    echo "Building frontend image..."
    echo "=============================================="

    docker build \
        --platform linux/amd64 \
        -t eap_frontend:$TAG \
        ./frontend

    echo "✓ Frontend image built: eap_frontend:$TAG"
    echo ""
fi

# Build router
if [ "$BUILD_ROUTER" = true ]; then
    echo "=============================================="
    echo "Building router image..."
    echo "=============================================="

    docker build \
        --platform linux/amd64 \
        -t eap_router:$TAG \
        ./router

    echo "✓ Router image built: eap_router:$TAG"
    echo ""
fi

echo "=============================================="
echo "Build complete!"
echo "=============================================="
echo ""
echo "To run locally with docker-compose:"
echo "  docker-compose up"
echo ""
echo "To push to Snowflake registry:"
echo "  snow spcs image-registry login"
echo "  docker tag eap_backend:$TAG <your-repo>/eap_backend:$TAG"
echo "  docker push <your-repo>/eap_backend:$TAG"
