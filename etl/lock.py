from .db import Database
from .logger import logger


class PgAdvisoryLock:
    DEFAULT_LOCK_ID = 123456789

    def __init__(self, db: Database, lock_id: int = None):
        self.db = db
        self.lock_id = lock_id if lock_id is not None else self.DEFAULT_LOCK_ID

    def __enter__(self):
        result = self.db.execute(
            "SELECT pg_try_advisory_lock(:lock_id)",
            {'lock_id': self.lock_id}
        ).fetchone()
        if not result[0]:
            raise Exception(f"ETL already running (advisory lock {self.lock_id} held)")
        logger.info(f"Acquired advisory lock {self.lock_id}")
        return self

    def __exit__(self, *args):
        self.db.execute("SELECT pg_advisory_unlock(:lock_id)", {'lock_id': self.lock_id})
        logger.info(f"Released advisory lock {self.lock_id}")
