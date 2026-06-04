from unittest.mock import patch

from etl.hr.config import HRConfig
from etl.hr.orchestrator import main as run_etl


def test_end_to_end_with_real_excel(pg_db, test_excel_file, test_mapping_file, monkeypatch):
    monkeypatch.setattr(HRConfig, "HR_EXCEL_PATH", test_excel_file)
    monkeypatch.setattr(HRConfig, "HR_SCHEMA_MAPPING_PATH", test_mapping_file)
    with patch("etl.hr.orchestrator.create_engine") as mock_engine:
        mock_engine.return_value = pg_db.engine
        exit_code = run_etl()
    assert exit_code == 0

    employees = pg_db.execute(
        "SELECT source_id, full_name FROM core.hr_employee ORDER BY source_id"
    )
    rows = employees.fetchall()
    assert len(rows) == 3
    expected = [
        ("001", "Иванов Иван Иванович"),
        ("002", "Петров Петр Петрович"),
        ("003", "Сидорова Анна Сергеевна"),
    ]
    assert rows == expected

    rejects = pg_db.execute("SELECT column_name, reject_reason FROM staging.hr_rejects")
    reasons = [r[1] for r in rejects.fetchall()]
    assert any("Invalid date format" in r for r in reasons)
    assert any("Missing mandatory field: full_name" in r for r in reasons)

    audit = pg_db.execute(
        "SELECT status, rows_extracted, rows_loaded, rows_rejected "
        "FROM audit.hr_etl_runs ORDER BY run_id DESC LIMIT 1"
    )
    status, extracted, loaded, rejected = audit.fetchone()
    assert status == "SUCCESS"
    assert extracted == 4
    assert loaded == 3
    assert rejected == 2
