import pandas as pd
from sqlalchemy import create_engine, text

from etl.config import Config


def get_engine():
    return create_engine(Config.DATABASE_URL)


def load_employees() -> pd.DataFrame:
    query = """
        SELECT
            source_id,
            full_name,
            responsible,
            position,
            department,
            gender,
            hire_date,
            state,
            harmful,
            electrical_safety,
            return_date,
            height,
            cradle,
            fire_safety,
            pmk_safety,
            special_assessment,
            is_dismissed,
            dismissed_at,
            last_seen_run_id,
            updated_at
        FROM core.hr_employee
        ORDER BY full_name
    """
    with get_engine().connect() as conn:
        return pd.read_sql(text(query), conn)


def load_etl_runs() -> pd.DataFrame:
    query = """
        SELECT
            run_id,
            started_at,
            finished_at,
            status,
            rows_extracted,
            rows_loaded,
            rows_rejected,
            excel_file_path,
            file_hash
        FROM audit.hr_etl_runs
        ORDER BY run_id DESC
        LIMIT 20
    """
    with get_engine().connect() as conn:
        return pd.read_sql(text(query), conn)


def load_reject_summary() -> pd.DataFrame:
    query = """
        SELECT reject_reason, COUNT(*) AS reject_count
        FROM staging.hr_rejects
        GROUP BY reject_reason
        ORDER BY reject_count DESC
        LIMIT 15
    """
    with get_engine().connect() as conn:
        return pd.read_sql(text(query), conn)


def load_last_run():
    query = """
        SELECT status, rows_loaded, rows_rejected, finished_at
        FROM audit.hr_etl_runs
        ORDER BY run_id DESC
        LIMIT 1
    """
    with get_engine().connect() as conn:
        return conn.execute(text(query)).fetchone()
