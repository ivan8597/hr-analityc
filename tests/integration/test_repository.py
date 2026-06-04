import pandas as pd

from etl.hr.repository import HRRepository


def test_insert_staging(pg_db, run_id):
    repo = HRRepository(pg_db)
    df = pd.DataFrame({
        "source_id": ["001", "002"],
        "full_name": ["Иванов", "Петров"],
        "run_id": [run_id, run_id],
        "row_id": [1, 2],
    })
    repo._insert_dataframe_in_batches(df, "staging", "hr_raw")
    result = pg_db.execute(
        "SELECT COUNT(*) FROM staging.hr_raw WHERE run_id = :run_id",
        {"run_id": run_id},
    )
    assert result.fetchone()[0] == 2


def test_upsert_employees(pg_db, clean_tables):
    repo = HRRepository(pg_db)
    df = pd.DataFrame({
        "source_id": ["A1", "A2"],
        "full_name": ["Employee 1", "Employee 2"],
        "position": ["Dev", "QA"],
    })
    repo.upsert_employees(df)
    df2 = pd.DataFrame({
        "source_id": ["A1"],
        "full_name": ["Employee 1 Updated"],
        "position": ["Senior Dev"],
    })
    repo.upsert_employees(df2)
    result = pg_db.execute(
        "SELECT full_name, position FROM core.hr_employee WHERE source_id = 'A1'"
    )
    row = result.fetchone()
    assert row[0] == "Employee 1 Updated"
    assert row[1] == "Senior Dev"


def test_insert_staging_empty(pg_db, run_id):
    repo = HRRepository(pg_db)
    df = pd.DataFrame(columns=["source_id", "full_name"])
    repo._insert_dataframe_in_batches(df, "staging", "hr_raw")
    result = pg_db.execute(
        "SELECT COUNT(*) FROM staging.hr_raw WHERE run_id = :run_id",
        {"run_id": run_id},
    )
    assert result.fetchone()[0] == 0
