from unittest.mock import patch

from etl.hr.config import HRConfig
from etl.hr.orchestrator import main


def test_orchestrator_success(pg_db, test_excel_file, test_mapping_file, monkeypatch):
    monkeypatch.setattr(HRConfig, "HR_EXCEL_PATH", test_excel_file)
    monkeypatch.setattr(HRConfig, "HR_SCHEMA_MAPPING_PATH", test_mapping_file)
    with patch("etl.hr.orchestrator.create_engine") as mock_engine:
        mock_engine.return_value = pg_db.engine
        exit_code = main()
    assert exit_code == 0
    audit = pg_db.execute(
        "SELECT status, rows_extracted, rows_loaded, rows_rejected "
        "FROM audit.hr_etl_runs ORDER BY run_id DESC LIMIT 1"
    )
    status, extracted, loaded, rejected = audit.fetchone()
    assert status == "SUCCESS"
    assert extracted == 4
    assert loaded == 3
    assert rejected == 2


def test_orchestrator_skips_already_processed(pg_db, test_excel_file, test_mapping_file, monkeypatch):
    monkeypatch.setattr(HRConfig, "HR_EXCEL_PATH", test_excel_file)
    monkeypatch.setattr(HRConfig, "HR_SCHEMA_MAPPING_PATH", test_mapping_file)
    with patch("etl.hr.orchestrator.create_engine") as mock_engine:
        mock_engine.return_value = pg_db.engine
        main()
    with patch("etl.hr.orchestrator.create_engine") as mock_engine:
        mock_engine.return_value = pg_db.engine
        exit_code = main()
    assert exit_code == 0
    runs = pg_db.execute("SELECT COUNT(*) FROM audit.hr_etl_runs WHERE status = 'SUCCESS'")
    assert runs.fetchone()[0] == 1


def test_orchestrator_file_not_found(monkeypatch):
    monkeypatch.setattr(HRConfig, "HR_EXCEL_PATH", "/nonexistent/file.xls")
    exit_code = main()
    assert exit_code == 1
