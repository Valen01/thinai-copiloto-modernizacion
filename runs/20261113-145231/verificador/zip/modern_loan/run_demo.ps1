# Equivalente a `make demo`: ejecuta el lote de liquidacion para los tenants de ejemplo.
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot
$python = if ($env:PYTHON) { $env:PYTHON } else { "python" }
$processDate = if ($env:PROCESS_DATE) { $env:PROCESS_DATE } else { "2026-03-31" }
$env:PYTHONPATH = "src"
foreach ($tenant in @("TENANT_A", "TENANT_B")) {
    & $python -m claims_settlement.adapters.inbound.batch `
        --tenant $tenant --data-dir examples --out-dir out --process-date $processDate
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
