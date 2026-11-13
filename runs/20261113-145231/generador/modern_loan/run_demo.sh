#!/usr/bin/env sh
# Equivalente a `make demo`: ejecuta el lote de liquidacion para los tenants de ejemplo.
set -eu
cd "$(dirname "$0")"
PYTHON="${PYTHON:-python3}"
PROCESS_DATE="${PROCESS_DATE:-2026-03-31}"
export PYTHONPATH="src"
for TENANT in TENANT_A TENANT_B; do
  "$PYTHON" -m claims_settlement.adapters.inbound.batch \
    --tenant "$TENANT" --data-dir examples --out-dir out --process-date "$PROCESS_DATE"
done
