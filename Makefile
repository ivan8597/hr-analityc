COMPOSE_PROJECT_NAME := hr_etl_project
DOCKER_COMPOSE := COMPOSE_PROJECT_NAME=$(COMPOSE_PROJECT_NAME) docker-compose

.PHONY: help build up down reset-db test install install-dev clean hr-etl dash \
	schedule-install schedule-uninstall schedule-status schedule-log

ETL_INTERVAL_MIN ?= 15
PLIST_DEST := $(HOME)/Library/LaunchAgents/com.hr-etl.plist

help:
	@echo "Available commands:"
	@echo "  make install     - Install Python dependencies"
	@echo "  make install-dev - Install dev dependencies (tests)"
	@echo "  make build       - Build Docker images"
	@echo "  make up          - Start PostgreSQL"
	@echo "  make down        - Stop containers"
	@echo "  make reset-db    - Stop containers and remove database volume"
	@echo "  make test        - Run tests"
	@echo "  make hr-etl      - Run HR ETL"
	@echo "  make dash        - Start HR dashboard"
	@echo "  make schedule-install   - Auto ETL every N min (launchd, default 15)"
	@echo "  make schedule-uninstall - Remove scheduled ETL"
	@echo "  make schedule-status    - Show launchd job status"
	@echo "  make schedule-log       - Tail ETL log"
	@echo "  make clean       - Clean temporary files"

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

build:
	$(DOCKER_COMPOSE) build

up:
	$(DOCKER_COMPOSE) up -d

down:
	$(DOCKER_COMPOSE) down

reset-db:
	$(DOCKER_COMPOSE) down -v

test:
	python -m pytest tests/ -v --cov=etl

hr-etl:
	python -m etl.hr.orchestrator

dash:
	python -m dashboard.app

schedule-install:
	@chmod +x scripts/run_scheduled_etl.sh
	@mkdir -p logs
	@INTERVAL_SEC=$$(($(ETL_INTERVAL_MIN)*60)); \
	sed -e 's|@PROJECT_DIR@|$(CURDIR)|g' \
		-e "s|@INTERVAL_SEC@|$$INTERVAL_SEC|g" \
		launchd/com.hr-etl.plist.template > $(PLIST_DEST)
	@launchctl bootout gui/$$(id -u)/com.hr-etl 2>/dev/null || true
	@launchctl bootstrap gui/$$(id -u) $(PLIST_DEST)
	@echo "Scheduled ETL every $(ETL_INTERVAL_MIN) min -> $(PLIST_DEST)"
	@echo "Logs: logs/etl.log"

schedule-uninstall:
	@launchctl bootout gui/$$(id -u)/com.hr-etl 2>/dev/null || true
	@rm -f $(PLIST_DEST)
	@echo "Scheduled ETL removed"

schedule-status:
	@launchctl print gui/$$(id -u)/com.hr-etl 2>/dev/null || echo "Not installed. Run: make schedule-install"

schedule-log:
	@tail -n 50 logs/etl.log 2>/dev/null || echo "No logs yet. Run: make schedule-install"

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
