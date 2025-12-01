#!/bin/bash

# =============================================================================
# BlendX Local Development Script
# Runs backend (FastAPI) and frontend (Vue) simultaneously
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Default ports
BACKEND_PORT=${API_PORT:-8081}
FRONTEND_PORT=${FRONTEND_PORT:-8080}

# PIDs for cleanup
BACKEND_PID=""
FRONTEND_PID=""

# =============================================================================
# Functions
# =============================================================================

print_header() {
    echo -e "${BLUE}"
    echo "=============================================="
    echo "   BlendX Local Development Environment"
    echo "=============================================="
    echo -e "${NC}"
}

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

cleanup() {
    echo ""
    print_info "Shutting down services..."

    if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        print_info "Stopping backend (PID: $BACKEND_PID)..."
        kill "$BACKEND_PID" 2>/dev/null || true
    fi

    if [ -n "$FRONTEND_PID" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
        print_info "Stopping frontend (PID: $FRONTEND_PID)..."
        kill "$FRONTEND_PID" 2>/dev/null || true
    fi

    # Kill any remaining processes on the ports
    lsof -ti:$BACKEND_PORT | xargs kill -9 2>/dev/null || true
    lsof -ti:$FRONTEND_PORT | xargs kill -9 2>/dev/null || true

    print_info "Cleanup complete. Goodbye!"
    exit 0
}

check_dependencies() {
    print_info "Checking dependencies..."

    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        exit 1
    fi

    # Check Node.js
    if ! command -v node &> /dev/null; then
        print_error "Node.js is not installed"
        exit 1
    fi

    # Check npm
    if ! command -v npm &> /dev/null; then
        print_error "npm is not installed"
        exit 1
    fi

    print_info "All dependencies found"
}

setup_backend() {
    print_info "Setting up backend..."

    cd "$PROJECT_ROOT/backend/app"

    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        print_info "Creating Python virtual environment..."
        python3 -m venv venv
    fi

    # Activate virtual environment
    source venv/bin/activate

    # Install dependencies
    print_info "Installing backend dependencies..."
    pip install -q -r requirements.txt

    cd "$PROJECT_ROOT"
}

setup_frontend() {
    print_info "Setting up frontend..."

    cd "$PROJECT_ROOT/frontend/vue"

    # Install dependencies if node_modules doesn't exist or package.json changed
    if [ ! -d "node_modules" ]; then
        print_info "Installing frontend dependencies..."
        npm install
    fi

    cd "$PROJECT_ROOT"
}

start_backend() {
    print_info "Starting backend on port $BACKEND_PORT..."

    cd "$PROJECT_ROOT/backend/app"
    source venv/bin/activate

    # Load environment variables if .env exists
    if [ -f "$PROJECT_ROOT/.env" ]; then
        export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
    fi

    # Set local development environment
    export ENVIRONMENT=local
    export API_PORT=$BACKEND_PORT

    # Run FastAPI with uvicorn
    python -m uvicorn main:app --host 0.0.0.0 --port $BACKEND_PORT --reload &
    BACKEND_PID=$!

    cd "$PROJECT_ROOT"

    # Wait for backend to be ready
    print_info "Waiting for backend to start..."
    for i in {1..30}; do
        if curl -s "http://localhost:$BACKEND_PORT/health" > /dev/null 2>&1; then
            print_info "Backend is ready!"
            break
        fi
        sleep 1
    done
}

start_frontend() {
    print_info "Starting frontend on port $FRONTEND_PORT..."

    cd "$PROJECT_ROOT/frontend/vue"

    # Run Vue development server
    npm run serve -- --port $FRONTEND_PORT &
    FRONTEND_PID=$!

    cd "$PROJECT_ROOT"
}

print_urls() {
    echo ""
    echo -e "${GREEN}=============================================="
    echo "   Services Running"
    echo "==============================================${NC}"
    echo ""
    echo -e "  ${BLUE}Backend API:${NC}  http://localhost:$BACKEND_PORT"
    echo -e "  ${BLUE}API Docs:${NC}     http://localhost:$BACKEND_PORT/docs"
    echo -e "  ${BLUE}Frontend:${NC}     http://localhost:$FRONTEND_PORT"
    echo ""
    echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
    echo ""
}

# =============================================================================
# Main
# =============================================================================

# Set up trap for cleanup on exit
trap cleanup SIGINT SIGTERM EXIT

print_header
check_dependencies

# Parse arguments
SKIP_SETUP=false
BACKEND_ONLY=false
FRONTEND_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-setup)
            SKIP_SETUP=true
            shift
            ;;
        --backend-only)
            BACKEND_ONLY=true
            shift
            ;;
        --frontend-only)
            FRONTEND_ONLY=true
            shift
            ;;
        --backend-port)
            BACKEND_PORT=$2
            shift 2
            ;;
        --frontend-port)
            FRONTEND_PORT=$2
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --skip-setup       Skip dependency installation"
            echo "  --backend-only     Run only the backend"
            echo "  --frontend-only    Run only the frontend"
            echo "  --backend-port N   Set backend port (default: 8081)"
            echo "  --frontend-port N  Set frontend port (default: 8080)"
            echo "  -h, --help         Show this help message"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Setup
if [ "$SKIP_SETUP" = false ]; then
    if [ "$FRONTEND_ONLY" = false ]; then
        setup_backend
    fi
    if [ "$BACKEND_ONLY" = false ]; then
        setup_frontend
    fi
fi

# Start services
if [ "$FRONTEND_ONLY" = false ]; then
    start_backend
fi

if [ "$BACKEND_ONLY" = false ]; then
    start_frontend
fi

print_urls

# Wait for processes
wait
