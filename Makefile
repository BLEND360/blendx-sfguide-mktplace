SNOWFLAKE_REPO=
BACKEND_IMAGE=eap_backend
FRONTEND_IMAGE=eap_frontend
ROUTER_IMAGE=eap_router

# Colors
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m

help:            ## Show this help.
	@echo "$(BLUE)BlendX - Available Commands$(NC)"
	@echo ""
	@echo "$(YELLOW)Local Development:$(NC)"
	@fgrep -h "## [Local]" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/## \[Local\]//'
	@echo ""
	@echo "$(YELLOW)Production Deployment:$(NC)"
	@fgrep -h "## [Prod]" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/## \[Prod\]//'
	@echo ""

all: login build push

login:           ## [Prod] Login to Snowflake Docker repo
	docker login $(SNOWFLAKE_REPO)

build: build_backend build_frontend build_router  ## [Prod] Build Docker images for Snowpark Container Services

build_backend:   ## [Prod] Build Docker image for backend for Snowpark Container Services
	cd backend && docker build --platform linux/amd64 -t $(BACKEND_IMAGE) . && cd ..

build_frontend:  ## [Prod] Build Docker image for frontend for Snowpark Container Services
	cd frontend && docker build --platform linux/amd64 -t $(FRONTEND_IMAGE) . && cd ..

build_router:    ## [Prod] Build Docker image for router for Snowpark Container Services
	cd router && docker build --platform linux/amd64 -t $(ROUTER_IMAGE) . && cd ..

push: push_backend push_frontend push_router     ## [Prod] Push Docker images to Snowpark Container Services

push_backend:    ## [Prod] Push backend Docker image to Snowpark Container Services
	docker tag $(BACKEND_IMAGE) $(SNOWFLAKE_REPO)/$(BACKEND_IMAGE)
	docker push $(SNOWFLAKE_REPO)/$(BACKEND_IMAGE)

push_frontend:   ## [Prod] Push frontend Docker image to Snowpark Container Services
	docker tag $(FRONTEND_IMAGE) $(SNOWFLAKE_REPO)/$(FRONTEND_IMAGE)
	docker push $(SNOWFLAKE_REPO)/$(FRONTEND_IMAGE)

push_router:     ## [Prod] Push router Docker image to Snowpark Container Services
	docker tag $(ROUTER_IMAGE) $(SNOWFLAKE_REPO)/$(ROUTER_IMAGE)
	docker push $(SNOWFLAKE_REPO)/$(ROUTER_IMAGE)

# ============================================================================
# Local Development Commands
# ============================================================================

dev-up:          ## [Local] Start all services with docker-compose
	@echo "$(BLUE)Starting all services...$(NC)"
	docker-compose up

dev-up-d:        ## [Local] Start all services in detached mode
	@echo "$(BLUE)Starting all services in detached mode...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)✓ Services started at http://localhost:8000$(NC)"

dev-down:        ## [Local] Stop all services
	@echo "$(YELLOW)Stopping all services...$(NC)"
	docker-compose down

dev-restart:     ## [Local] Restart all services
	$(MAKE) dev-down
	$(MAKE) dev-up-d

dev-build:       ## [Local] Build all Docker images for local development
	@echo "$(BLUE)Building all images...$(NC)"
	docker-compose build

dev-logs:        ## [Local] View logs from all services
	docker-compose logs -f

dev-clean:       ## [Local] Stop services and remove volumes
	@echo "$(YELLOW)Cleaning up containers and volumes...$(NC)"
	docker-compose down -v
	@echo "$(GREEN)✓ Cleanup complete$(NC)"

dev-shell-backend:  ## [Local] Open shell in backend container
	docker-compose exec backend /bin/bash

dev-shell-frontend: ## [Local] Open shell in frontend container
	docker-compose exec frontend /bin/sh

dev-setup:       ## [Local] Setup .env file from example
	@if [ -f .env ]; then \
		echo "$(YELLOW).env file already exists$(NC)"; \
	else \
		cp .env.example .env; \
		echo "$(GREEN)✓ .env created. Edit with your credentials$(NC)"; \
	fi

init:            ## [Local] Initialize development environment (hooks, pre-commit, .env)
	@echo "$(BLUE)Initializing development environment...$(NC)"
	@git config core.hooksPath .githooks
	@echo "$(GREEN)✓ Git hooks configured$(NC)"
	@pre-commit install
	@echo "$(GREEN)✓ Pre-commit hooks installed$(NC)"
	@$(MAKE) dev-setup
	@echo "$(GREEN)✓ Development environment ready$(NC)"

requirements:    ## Regenerate backend/requirements.txt from pyproject.toml
	@echo "$(BLUE)Regenerating requirements.txt...$(NC)"
	cd backend && uv export --no-hashes --no-dev -o requirements.txt
	@echo "$(GREEN)✓ requirements.txt updated$(NC)"

check-requirements: ## Verify requirements.txt is in sync with pyproject.toml
	@echo "$(BLUE)Checking requirements.txt sync...$(NC)"
	@cd backend && uv export --no-hashes --no-dev -o /tmp/requirements-check.txt 2>/dev/null && \
	if ! diff -q <(grep -v "^#" requirements.txt | sort) <(grep -v "^#" /tmp/requirements-check.txt | sort) > /dev/null 2>&1; then \
		echo "$(YELLOW)requirements.txt is out of sync with pyproject.toml$(NC)"; \
		echo "Run: make requirements"; \
		exit 1; \
	fi
	@echo "$(GREEN)✓ requirements.txt is in sync$(NC)"
