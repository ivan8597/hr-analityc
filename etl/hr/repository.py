import pandas as pd
from psycopg2.extras import execute_values

from ..db import Database
from ..logger import logger
from .config import HRConfig


class HRRepository:
    def __init__(self, db: Database):
        self.db = db

    def insert_staging(self, df: pd.DataFrame, run_id: int, file_hash: str, file_mtime):
        staging_df = df.copy()
        staging_df['run_id'] = run_id
        staging_df['row_id'] = range(1, len(staging_df) + 1)
        self._insert_dataframe_in_batches(staging_df, 'staging', 'hr_raw')
        logger.info(f"Inserted {len(staging_df)} rows into staging.hr_raw")

    def upsert_employees(self, employees_df: pd.DataFrame, run_id: int):
        if employees_df.empty:
            logger.info("No HR employees to upsert")
            return
        employees_df = employees_df.copy()
        employees_df['is_dismissed'] = False
        employees_df['dismissed_at'] = None
        employees_df['last_seen_run_id'] = run_id
        columns = employees_df.columns.tolist()
        update_cols = [c for c in columns if c != 'source_id']
        update_set = ', '.join([f"{col} = EXCLUDED.{col}" for col in update_cols])
        sql = f"""
            INSERT INTO core.hr_employee ({', '.join(columns)})
            VALUES %s
            ON CONFLICT (source_id) DO UPDATE SET
                {update_set},
                updated_at = CURRENT_TIMESTAMP
        """
        values = [tuple(None if pd.isna(v) else v for v in row) for row in employees_df.to_numpy()]
        total = len(values)
        with self.db.get_raw_connection() as conn:
            cur = conn.cursor()
            for i in range(0, total, HRConfig.BATCH_SIZE):
                batch = values[i:i + HRConfig.BATCH_SIZE]
                execute_values(cur, sql, batch, page_size=1000)
                logger.debug(f"Upserted batch {i // HRConfig.BATCH_SIZE + 1} ({len(batch)} rows)")
            conn.commit()
        logger.info(f"Upserted {total} HR employees")

    def mark_missing_as_dismissed(self, current_source_ids: list[str], run_id: int) -> int:
        if not current_source_ids:
            logger.warning("No current source IDs found; skipping dismissal marking")
            return 0

        values = [(source_id,) for source_id in current_source_ids]
        sql = """
            UPDATE core.hr_employee AS employee
            SET
                is_dismissed = TRUE,
                dismissed_at = COALESCE(employee.dismissed_at, CURRENT_TIMESTAMP),
                updated_at = CURRENT_TIMESTAMP
            WHERE employee.source_id NOT IN (
                SELECT source_id FROM (VALUES %s) AS current_employees(source_id)
            )
            AND employee.is_dismissed = FALSE
        """
        with self.db.get_raw_connection() as conn:
            cur = conn.cursor()
            execute_values(cur, sql, values, template="(%s)", page_size=HRConfig.BATCH_SIZE)
            affected = cur.rowcount
            conn.commit()

        logger.info(f"Marked {affected} HR employees as dismissed for run {run_id}")
        return affected

    def _insert_dataframe_in_batches(self, df: pd.DataFrame, schema: str, table: str):
        if df.empty:
            return
        columns = list(df.columns)
        values = [tuple(None if pd.isna(v) else v for v in row) for row in df.to_numpy()]
        sql = f"INSERT INTO {schema}.{table} ({', '.join(columns)}) VALUES %s"
        with self.db.get_raw_connection() as conn:
            cur = conn.cursor()
            for i in range(0, len(values), HRConfig.BATCH_SIZE):
                batch = values[i:i + HRConfig.BATCH_SIZE]
                execute_values(cur, sql, batch, page_size=1000)
            conn.commit()
