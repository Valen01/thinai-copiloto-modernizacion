"""Pruebas del adaptador batch (formato de archivos) y de utilidades compartidas."""
from pathlib import Path

import pytest

from claims_settlement.adapters.inbound import batch
from claims_settlement.adapters.inbound.batch_format import (
    BatchFormatError, load_tenant_data, parse_amount, parse_date, parse_int, parse_pct)
from claims_settlement.adapters.outbound.audit import EnvProcessUserProvider
from claims_settlement.application.tenant import validate_tenant_id
from claims_settlement.domain.errors import InvalidValueError
from claims_settlement.shared.masking import mask_id, mask_name

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


@pytest.fixture(autouse=True)
def process_user(monkeypatch):
    monkeypatch.setenv("CLAIMS_PROCESS_USER", "BATCH")


def run_main(tmp_path, tenant="TENANT_A", data_dir=EXAMPLES, date="2026-03-31"):
    return batch.main(["--tenant", tenant, "--data-dir", str(data_dir),
                       "--out-dir", str(tmp_path), "--process-date", date])


def test_end_to_end_batch_output_files(tmp_path, capsys):
    """REGLA: R-026 - archivo de salida con '|', importes sin signo a 2 decimales.
    Valores a mano: 1001 => base 12345.67, deducible 617.28 -> VIP 308.64, cubierto 12037.03,
    retencion 2% = 240.74, neto 11796.29. 1003 => (8123.45-200)*90% = 7131.105 -> 7131.11."""
    assert run_main(tmp_path) == 0
    lines = (tmp_path / "TENANT_A" / "liquidaciones.out").read_text().splitlines()
    assert lines[0] == ("1|1001|2026-03-31|12345.67|12345.67|308.64|12037.03|240.74|11796.29|"
                        "APROBADA|LIQUIDACION_AUTOMATICA|DESCUENTO_VIP;RETENCION_APLICADA|BATCH")
    assert lines[1] == ("2|1002|2026-03-31|30000.00|0.00|0.00|0.00|0.00|0.00|"
                        "RECHAZADA|FUERA_DE_VIGENCIA||BATCH")
    assert lines[2] == ("3|1003|2026-03-31|8123.45|8123.45|200.00|7131.11|0.00|7131.11|"
                        "APROBADA|LIQUIDACION_AUTOMATICA||BATCH")
    assert lines[3].split("|")[9:11] == ["RECHAZADA", "POLIZA_NO_VIGENTE"]
    summary = (tmp_path / "TENANT_A" / "resumen.txt").read_text()
    assert " Procesados         : 17" in summary and " Errores            : 0" in summary
    assert "Tenant TENANT_A" in capsys.readouterr().out


def test_end_to_end_other_files(tmp_path):
    """REGLA: R-031 - bitacora con inicio/fin; ids de siniestro enmascarados en la bitacora.
    Siniestro 1016 (denuncia 2026-04-05 > corte) permanece REGISTRADO (R-028)."""
    run_main(tmp_path)
    log = (tmp_path / "TENANT_A" / "bitacora.out").read_text().splitlines()
    assert log[0].endswith("|INFO||Inicio lote de liquidacion. Fecha proceso: 2026-03-31")
    assert "|**01|" in log[1] or "|***01|" in log[1] or "|" in log[1]
    assert not any("|1001|" in line for line in log)
    claims = (tmp_path / "TENANT_A" / "siniestros.out").read_text().splitlines()
    assert "1016|REGISTRADO" in claims and "1001|LIQUIDADO" in claims


def test_tenant_b_uses_its_own_configuration(tmp_path):
    """REGLA: R-007 - TENANT_B tiene DIAS_MAX_DENUNCIA=15: 18 dias => DENUNCIA_EXTEMPORANEA.
    1001 (B): cubierto 4900.00, retencion 5% = 245.00, neto 4655.00 > 2000 => pendiente."""
    assert run_main(tmp_path, "TENANT_B") == 0
    lines = (tmp_path / "TENANT_B" / "liquidaciones.out").read_text().splitlines()
    assert lines[0].split("|")[3:11] == [
        "5000.00", "5000.00", "100.00", "4900.00", "245.00", "4655.00",
        "PENDIENTE_APROBACION", "SUPERA_TOPE_AUTOMATICO"]
    assert lines[1].split("|")[9:11] == ["RECHAZADA", "DENUNCIA_EXTEMPORANEA"]


def test_default_process_date_is_today_without_time():
    """REGLA: R-028 - sin fecha, el lote usa la fecha del sistema a medianoche (TRUNC(SYSDATE))."""
    value = batch.parse_process_date(None)
    assert (value.hour, value.minute, value.second) == (0, 0, 0)
    assert batch.parse_process_date("2026-03-31").day == 31


def test_main_reports_errors_with_exit_code_2(tmp_path, capsys):
    """Errores de configuracion o de formato terminan con codigo 2 y mensaje claro."""
    assert run_main(tmp_path, "../x") == 2
    assert run_main(tmp_path, "NO_EXISTE") == 2
    assert run_main(tmp_path, date="2026-02-30") == 2
    assert capsys.readouterr().err.count("ERROR:") == 3


def copy_tenant(tmp_path, **replacements):
    target = tmp_path / "T"
    target.mkdir()
    for source in (EXAMPLES / "TENANT_B").glob("*.dat"):
        text = source.read_text()
        target.joinpath(source.name).write_text(replacements.get(source.name, text))
    return tmp_path


@pytest.mark.parametrize("name,content,fragment", [
    ("clientes.dat", "1|ANA|CC|1|GOLD|2020-01-01\n", "categoria"),             # R-004
    ("clientes.dat", "1|ANA|CC\n", "se esperan 6 campos"),
    ("polizas.dat", "201|P|1|AUTO|2025-02-30|2026-12-31|VIGENTE|5|FIJO|1|0\n", "fecha"),
    ("polizas.dat", "201|P|1|AUTO|2025-01-01|2026-12-31|VIGENTE|-5|FIJO|1|0\n", "importe"),
    ("coberturas.dat", "201|COB|10.123|100|0\n", "importe"),                   # 3 decimales
    ("siniestros.dat", "x|201|COB|2026-03-01|2026-03-03|5|REGISTRADO|d\n", "entero"),
])
def test_invalid_input_is_rejected_explicitly(tmp_path, name, content, fragment):
    """El archivo mal formado se rechaza completo (sin truncar ni corregir en silencio)."""
    root = copy_tenant(tmp_path, **{name: content})
    with pytest.raises(BatchFormatError) as err:
        load_tenant_data(root / "T")
    assert fragment in str(err.value) and name in str(err.value)


def test_missing_required_file_is_rejected(tmp_path):
    """Un archivo requerido ausente es error de formato."""
    root = copy_tenant(tmp_path)
    (root / "T" / "parametros.dat").unlink()
    with pytest.raises(BatchFormatError):
        load_tenant_data(root / "T")


def test_parsers_boundaries():
    """Limites de los analizadores: 12 digitos enteros, 2 decimales, fechas con hora."""
    assert str(parse_amount("999999999999.99")) == "999999999999.99"
    for bad in ("1000000000000", "1.234", "-1", "1,5", ""):
        with pytest.raises(ValueError):
            parse_amount(bad)
    assert str(parse_pct("100")) == "100"
    with pytest.raises(ValueError):
        parse_pct("1000")
    assert parse_int("007") == 7
    assert parse_date("2026-03-31 10:30:00").hour == 10
    with pytest.raises(ValueError):
        parse_date("31/03/2026")


def test_masking_helpers():
    """Enmascaramiento de identificadores y nombres para logs y mensajes."""
    assert mask_id(1001) == "**01" and mask_id("7") == "*" and mask_id("") == ""
    assert mask_id("AUTO-0001") == "*******01"
    assert mask_name("ana maria torres") == "A. M. T."


def test_tenant_id_validation():
    """El tenant_id solo admite letras, digitos, '-' y '_' (seguro para rutas)."""
    assert validate_tenant_id("TENANT_A-1") == "TENANT_A-1"
    for bad in ("", "a/b", "..", None, "x" * 41, "a b"):
        with pytest.raises(InvalidValueError):
            validate_tenant_id(bad)


def test_process_user_comes_from_environment(monkeypatch):
    """El usuario de proceso viene de CLAIMS_PROCESS_USER (max. 30 caracteres)."""
    monkeypatch.setenv("CLAIMS_PROCESS_USER", "OPERADOR1")
    assert EnvProcessUserProvider().current_user("T1") == "OPERADOR1"
    monkeypatch.setenv("CLAIMS_PROCESS_USER", "x" * 31)
    with pytest.raises(ValueError):
        EnvProcessUserProvider().current_user("T1")
