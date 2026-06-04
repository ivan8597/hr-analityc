import json
from threading import Lock

import pandas as pd
from psycopg2.extras import execute_values

from ..db import Database
from ..logger import logger
from .config import HRConfig


def _sanitize_value(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def _serialize_row(row: dict) -> str:
    cleaned = {key: _sanitize_value(val) for key, val in row.items()}
    return json.dumps(cleaned, ensure_ascii=False, default=str)


class RejectLogger:
    def __init__(self, db: Database, run_id: int):
        self.db = db
        self.run_id = run_id
        self.buffer = []
        self.batch_size = HRConfig.REJECT_BATCH_SIZE
        self.lock = Lock()

    def log_reject(self, row: dict, column_name: str, raw_value: str, reason: str):
        with self.lock:
            self.buffer.append({
                'run_id': self.run_id,
                'source_row': _serialize_row(row),
                'column_name': column_name,
                'raw_value': str(raw_value) if raw_value is not None else None,
                'reject_reason': reason
            })
            if len(self.buffer) >= self.batch_size:
                self._flush_unlocked()

    def flush(self):
        with self.lock:
            self._flush_unlocked()

    def _flush_unlocked(self):
        if not self.buffer:
            return
        with self.db.get_raw_connection() as conn:
            cur = conn.cursor()
            values = [
                (r['run_id'], r['source_row'], r['column_name'], r['raw_value'], r['reject_reason'])
                for r in self.buffer
            ]
            execute_values(
                cur,
                """
                INSERT INTO staging.hr_rejects
                (run_id, source_row, column_name, raw_value, reject_reason)
                VALUES %s
                """,
                values,
                page_size=1000
            )
            conn.commit()
        logger.info(f"Flushed {len(self.buffer)} reject records to staging.hr_rejects")
        self.buffer.clear()
