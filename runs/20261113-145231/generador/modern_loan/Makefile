PYTHON ?= python3
GATE ?= ../../tools/gate_codigo.py
RULES ?= ../../validador/reglas_limpias.json
PROCESS_DATE ?= 2026-03-31

export PYTHONPATH := src

.PHONY: demo test gate

# Un solo comando: ejecuta el lote de los dos tenants de ejemplo y deja la salida en out/
demo:
	$(PYTHON) -m claims_settlement.adapters.inbound.batch --tenant TENANT_A --data-dir examples --out-dir out --process-date $(PROCESS_DATE)
	$(PYTHON) -m claims_settlement.adapters.inbound.batch --tenant TENANT_B --data-dir examples --out-dir out --process-date $(PROCESS_DATE)

test:
	$(PYTHON) -m pytest tests -q

# Compuerta de calidad (no modificar el script ni los umbrales)
gate:
	$(PYTHON) -I $(GATE) . $(RULES)
