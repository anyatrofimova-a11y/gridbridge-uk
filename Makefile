# Makefile
# GridBridge UK - Build and Run Automation
#
# Usage:
#   make help          Show available targets
#   make build         Build Docker image
#   make run           Run single ingestion
#   make test          Run test suite
#   make clean         Remove outputs and containers

# ============================================================================
# Configuration
# ============================================================================

SHELL := /bin/bash
.DEFAULT_GOAL := help

# Project settings
PROJECT_NAME := gridbridge-uk
IMAGE_NAME := gridbridge-uk
IMAGE_TAG := latest

# Default parameters (can be overridden: make run START_DATE=2025-02-01)
START_DATE ?= 2025-01-15
DAYS ?= 1
OUTPUT_DIR ?= ./out

# Docker settings
DOCKER_COMPOSE := docker-compose
DOCKER := docker

# Colours for terminal output
CYAN := \033[0;36m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m  # No colour

# ============================================================================
# Help
# ============================================================================

.PHONY: help
help: ## Show this help message
	@echo ""
	@echo "$(CYAN)GridBridge UK - Data Ingestion & Analysis Platform$(NC)"
	@echo ""
	@echo "$(GREEN)Usage:$(NC)"
	@echo "  make <target> [VARIABLE=value]"
	@echo ""
	@echo "$(GREEN)Targets:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(GREEN)Variables:$(NC)"
	@echo "  $(CYAN)START_DATE$(NC)         Start date for ingestion (default: $(START_DATE))"
	@echo "  $(CYAN)DAYS$(NC)               Number of days to ingest (default: $(DAYS))"
	@echo "  $(CYAN)OUTPUT_DIR$(NC)         Output directory (default: $(OUTPUT_DIR))"
	@echo ""
	@echo "$(GREEN)Examples:$(NC)"
	@echo "  make run START_DATE=2025-02-01 DAYS=7"
	@echo "  make test"
	@echo "  make shell"
	@echo ""

# ============================================================================
# Build Targets
# ============================================================================

.PHONY: build
build: ## Build Docker image
	@echo "$(CYAN)Building Docker image...$(NC)"
	$(DOCKER) build -t $(IMAGE_NAME):$(IMAGE_TAG) .
	@echo "$(GREEN)Build complete: $(IMAGE_NAME):$(IMAGE_TAG)$(NC)"

.PHONY: build-no-cache
build-no-cache: ## Build Docker image without cache
	@echo "$(CYAN)Building Docker image (no cache)...$(NC)"
	$(DOCKER) build --no-cache -t $(IMAGE_NAME):$(IMAGE_TAG) .
	@echo "$(GREEN)Build complete: $(IMAGE_NAME):$(IMAGE_TAG)$(NC)"

.PHONY: pull
pull: ## Pull base images
	$(DOCKER) pull python:3.11-slim-bookworm

# ============================================================================
# Run Targets
# ============================================================================

.PHONY: run
run: build ## Run single ingestion with default or specified parameters
	@echo "$(CYAN)Running ingestion: $(START_DATE) for $(DAYS) day(s)$(NC)"
	@mkdir -p $(OUTPUT_DIR)
	GRIDBRIDGE_START_DATE=$(START_DATE) \
	GRIDBRIDGE_DAYS=$(DAYS) \
	$(DOCKER_COMPOSE) run --rm gridbridge
	@echo "$(GREEN)Complete. Outputs in $(OUTPUT_DIR)/$(NC)"

.PHONY: run-local
run-local: ## Run ingestion locally (no Docker)
	@echo "$(CYAN)Running locally...$(NC)"
	@mkdir -p $(OUTPUT_DIR)
	python examples/ingest_real_data.py \
		--start $(START_DATE) \
		--days $(DAYS) \
		--output $(OUTPUT_DIR)
	@echo "$(GREEN)Complete. Outputs in $(OUTPUT_DIR)/$(NC)"

.PHONY: run-week
run-week: build ## Run ingestion for past 7 days
	@echo "$(CYAN)Running 7-day ingestion...$(NC)"
	@mkdir -p $(OUTPUT_DIR)
	GRIDBRIDGE_START_DATE=$$(date -d '7 days ago' +%Y-%m-%d) \
	GRIDBRIDGE_DAYS=7 \
	$(DOCKER_COMPOSE) run --rm gridbridge
	@echo "$(GREEN)Complete.$(NC)"

.PHONY: run-scheduled
run-scheduled: build ## Start scheduled ingestion service (runs every 6 hours)
	@echo "$(CYAN)Starting scheduled service...$(NC)"
	$(DOCKER_COMPOSE) --profile scheduled up -d gridbridge-scheduler
	@echo "$(GREEN)Scheduler running. View logs: make logs-scheduler$(NC)"

.PHONY: stop-scheduled
stop-scheduled: ## Stop scheduled ingestion service
	@echo "$(CYAN)Stopping scheduler...$(NC)"
	$(DOCKER_COMPOSE) --profile scheduled down
	@echo "$(GREEN)Scheduler stopped.$(NC)"

# ============================================================================
# Development Targets
# ============================================================================

.PHONY: shell
shell: build ## Open interactive shell in container
	@echo "$(CYAN)Opening development shell...$(NC)"
	$(DOCKER_COMPOSE) --profile dev run --rm gridbridge-dev

.PHONY: ipython
ipython: build ## Open IPython shell with data loaded
	@echo "$(CYAN)Opening IPython...$(NC)"
	$(DOCKER) run --rm -it \
		-v $(PWD)/out:/app/out:ro \
		-v $(PWD)/examples:/app/examples:ro \
		$(IMAGE_NAME):$(IMAGE_TAG) \
		python -c "import pandas as pd; import pypsa; df = pd.read_parquet('/app/out/canonical.parquet') if __import__('pathlib').Path('/app/out/canonical.parquet').exists() else pd.DataFrame(); print(f'Loaded {len(df)} rows'); import code; code.interact(local=locals())"

.PHONY: lint
lint: ## Run linters (local Python)
	@echo "$(CYAN)Running linters...$(NC)"
	python -m flake8 examples/ --max-line-length=100 --ignore=E501,W503
	python -m black examples/ --check --diff
	@echo "$(GREEN)Lint passed.$(NC)"

.PHONY: format
format: ## Format code with black
	@echo "$(CYAN)Formatting code...$(NC)"
	python -m black examples/
	@echo "$(GREEN)Formatting complete.$(NC)"

# ============================================================================
# Test Targets
# ============================================================================

.PHONY: test
test: build ## Run test suite in container
	@echo "$(CYAN)Running tests...$(NC)"
	$(DOCKER_COMPOSE) --profile test run --rm gridbridge-test
	@echo "$(GREEN)Tests complete.$(NC)"

.PHONY: test-local
test-local: ## Run tests locally
	@echo "$(CYAN)Running tests locally...$(NC)"
	pytest tests/ -v --tb=short
	@echo "$(GREEN)Tests complete.$(NC)"

.PHONY: test-quick
test-quick: build ## Run quick smoke test (single day, minimal validation)
	@echo "$(CYAN)Running smoke test...$(NC)"
	@mkdir -p $(OUTPUT_DIR)/test
	$(DOCKER) run --rm \
		-v $(PWD)/out/test:/app/out:rw \
		$(IMAGE_NAME):$(IMAGE_TAG) \
		--start 2025-01-15 --days 1 --output /app/out
	@if [ -f "$(OUTPUT_DIR)/test/canonical.parquet" ]; then \
		echo "$(GREEN)Smoke test PASSED: canonical.parquet created$(NC)"; \
	else \
		echo "$(RED)Smoke test FAILED: no output$(NC)"; \
		exit 1; \
	fi

.PHONY: test-integration
test-integration: build ## Run full integration test (7 days, all validations)
	@echo "$(CYAN)Running integration test (this may take a few minutes)...$(NC)"
	@mkdir -p $(OUTPUT_DIR)/integration
	$(DOCKER) run --rm \
		-v $(PWD)/out/integration:/app/out:rw \
		$(IMAGE_NAME):$(IMAGE_TAG) \
		--start 2025-01-01 --days 7 --output /app/out
	@python -c " \
import pandas as pd; \
import json; \
df = pd.read_parquet('$(OUTPUT_DIR)/integration/canonical.parquet'); \
assert len(df) >= 48 * 7, f'Expected >=336 rows, got {len(df)}'; \
assert 'demand_mw' in df.columns, 'Missing demand_mw'; \
assert df['demand_mw'].notna().mean() > 0.5, 'Too many missing demand values'; \
print('Integration test PASSED'); \
"
	@echo "$(GREEN)Integration test complete.$(NC)"

# ============================================================================
# Output & Logging
# ============================================================================

.PHONY: logs
logs: ## Show logs from last run
	$(DOCKER_COMPOSE) logs gridbridge

.PHONY: logs-scheduler
logs-scheduler: ## Show scheduler logs
	$(DOCKER_COMPOSE) --profile scheduled logs -f gridbridge-scheduler

.PHONY: inspect-output
inspect-output: ## Inspect canonical.parquet output
	@if [ -f "$(OUTPUT_DIR)/canonical.parquet" ]; then \
		python -c " \
import pandas as pd; \
df = pd.read_parquet('$(OUTPUT_DIR)/canonical.parquet'); \
print('=== Canonical Data Summary ==='); \
print(f'Shape: {df.shape}'); \
print(f'Time range: {df.index.min()} to {df.index.max()}'); \
print(f'Columns: {list(df.columns)}'); \
print(); \
print('=== Sample (first 5 rows) ==='); \
print(df.head()); \
print(); \
print('=== Statistics ==='); \
print(df.describe().round(1)); \
"; \
	else \
		echo "$(RED)No output found at $(OUTPUT_DIR)/canonical.parquet$(NC)"; \
		echo "Run 'make run' first."; \
	fi

.PHONY: inspect-audit
inspect-audit: ## Show audit trail
	@if ls $(OUTPUT_DIR)/audit/*.json 1>/dev/null 2>&1; then \
		for f in $(OUTPUT_DIR)/audit/*.json; do \
			echo "$(CYAN)=== $$f ===$(NC)"; \
			python -m json.tool "$$f"; \
		done; \
	else \
		echo "$(RED)No audit files found in $(OUTPUT_DIR)/audit/$(NC)"; \
	fi

.PHONY: inspect-network
inspect-network: ## Summarise PyPSA network snapshot
	@if [ -f "$(OUTPUT_DIR)/pypsa_snapshot.nc" ]; then \
		python -c " \
import pypsa; \
net = pypsa.Network('$(OUTPUT_DIR)/pypsa_snapshot.nc'); \
print('=== PyPSA Network Summary ==='); \
print(f'Buses: {len(net.buses)}'); \
print(f'Generators: {len(net.generators)}'); \
print(f'Lines: {len(net.lines)}'); \
print(f'Loads: {len(net.loads)}'); \
print(f'Snapshots: {len(net.snapshots)}'); \
print(); \
print('=== Buses ==='); \
print(net.buses); \
print(); \
print('=== Generators ==='); \
print(net.generators[['bus', 'p_nom', 'carrier', 'marginal_cost']]); \
"; \
	else \
		echo "$(RED)No network found at $(OUTPUT_DIR)/pypsa_snapshot.nc$(NC)"; \
	fi

# ============================================================================
# Cleanup
# ============================================================================

.PHONY: clean
clean: ## Remove output files and stopped containers
	@echo "$(CYAN)Cleaning up...$(NC)"
	rm -rf $(OUTPUT_DIR)/*
	$(DOCKER_COMPOSE) down --remove-orphans 2>/dev/null || true
	@echo "$(GREEN)Clean complete.$(NC)"

.PHONY: clean-all
clean-all: clean ## Remove outputs, containers, and images
	@echo "$(CYAN)Removing Docker images...$(NC)"
	$(DOCKER) rmi $(IMAGE_NAME):$(IMAGE_TAG) 2>/dev/null || true
	$(DOCKER) image prune -f
	@echo "$(GREEN)Full clean complete.$(NC)"

.PHONY: clean-docker
clean-docker: ## Remove all project Docker resources
	@echo "$(CYAN)Removing all Docker resources...$(NC)"
	$(DOCKER_COMPOSE) down --rmi all --volumes --remove-orphans 2>/dev/null || true
	@echo "$(GREEN)Docker cleanup complete.$(NC)"

# ============================================================================
# CI/CD Targets
# ============================================================================

.PHONY: ci-build
ci-build: ## CI: Build and tag image
	@echo "$(CYAN)CI: Building image...$(NC)"
	$(DOCKER) build \
		--build-arg BUILD_DATE=$$(date -u +"%Y-%m-%dT%H:%M:%SZ") \
		--build-arg VCS_REF=$$(git rev-parse --short HEAD 2>/dev/null || echo "unknown") \
		-t $(IMAGE_NAME):$(IMAGE_TAG) \
		-t $(IMAGE_NAME):$$(git rev-parse --short HEAD 2>/dev/null || echo "latest") \
		.

.PHONY: ci-test
ci-test: ci-build test-quick ## CI: Build and run smoke test
	@echo "$(GREEN)CI tests passed.$(NC)"

.PHONY: ci-full
ci-full: ci-build test-quick test-integration ## CI: Full test suite
	@echo "$(GREEN)Full CI suite passed.$(NC)"

.PHONY: ci-push
ci-push: ## CI: Push image to registry (requires DOCKER_REGISTRY env var)
	@if [ -z "$(DOCKER_REGISTRY)" ]; then \
		echo "$(RED)DOCKER_REGISTRY not set$(NC)"; \
		exit 1; \
	fi
	$(DOCKER) tag $(IMAGE_NAME):$(IMAGE_TAG) $(DOCKER_REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)
	$(DOCKER) push $(DOCKER_REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)
	@echo "$(GREEN)Pushed to $(DOCKER_REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)$(NC)"

# ============================================================================
# Utility Targets
# ============================================================================

.PHONY: version
version: ## Show version info
	@echo "$(CYAN)GridBridge UK$(NC)"
	@echo "  Image: $(IMAGE_NAME):$(IMAGE_TAG)"
	@echo "  Git:   $$(git rev-parse --short HEAD 2>/dev/null || echo 'not a git repo')"
	@echo "  Date:  $$(date -Iseconds)"

.PHONY: deps
deps: ## Install local Python dependencies
	pip install --upgrade pip setuptools wheel
	pip install -r requirements.txt
	pip install flake8 black pytest pytest-cov

.PHONY: deps-dev
deps-dev: deps ## Install development dependencies
	pip install ipython jupyter matplotlib

.PHONY: env-template
env-template: ## Create .env template file
	@echo "# GridBridge UK Environment Configuration" > .env.template
	@echo "GRIDBRIDGE_START_DATE=2025-01-15" >> .env.template
	@echo "GRIDBRIDGE_DAYS=1" >> .env.template
	@echo "" >> .env.template
	@echo "# API Keys (optional)" >> .env.template
	@echo "ELEXON_API_KEY=" >> .env.template
	@echo "METOFFICE_API_KEY=" >> .env.template
	@echo "" >> .env.template
	@echo "# Docker Registry (for CI/CD)" >> .env.template
	@echo "DOCKER_REGISTRY=" >> .env.template
	@echo "$(GREEN)Created .env.template$(NC)"

# ============================================================================
# Phony declarations
# ============================================================================

.PHONY: all
all: build test-quick ## Build and run smoke test
