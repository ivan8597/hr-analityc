#!/usr/bin/env bash
# Запуск HR ETL по расписанию (launchd / cron).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

mkdir -p logs
TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S')"
echo "[$TIMESTAMP] scheduled ETL start" >> logs/etl.log

if [[ ! -f .venv/bin/python ]]; then
  echo "[$TIMESTAMP] ERROR: .venv not found. Run: python3 -m venv .venv && pip install -r requirements.txt" >> logs/etl.log
  exit 1
fi

export COMPOSE_PROJECT_NAME=hr_etl_project
docker compose up -d >> logs/etl.log 2>&1 || true

# shellcheck disable=SC1091
source .venv/bin/activate
python -m etl.hr.orchestrator >> logs/etl.log 2>&1
echo "[$TIMESTAMP] scheduled ETL done (exit $?)" >> logs/etl.log
