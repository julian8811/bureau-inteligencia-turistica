#!/bin/bash
# Instala el cron diario del Bureau: ETL 06:00 COT -> logs/cron.log
# Uso: bash etl-bureau/orchestration/cron_install.sh
set -e
REPO="/home/julian/Bureau"
PY="/home/julian/miniconda3/bin/python3"
SCRIPT="$REPO/etl-bureau/orchestration/daily.py"
LOG="$REPO/etl-bureau/logs/cron.log"
mkdir -p "$REPO/etl-bureau/logs"
ENV_FILE="$HOME/.bureau_backend_env"
LINE="0 6 * * * . $ENV_FILE 2>/dev/null; $PY $SCRIPT >> $LOG 2>&1"
(crontab -l 2>/dev/null | grep -v "etl-bureau/orchestration/daily.py" || true; echo "$LINE") | crontab -
echo "cron instalado:"
crontab -l | grep "etl-bureau/orchestration/daily.py" || true
