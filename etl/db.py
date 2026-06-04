from contextlib import contextmanager

from sqlalchemy import text

from .config import Config
from .logger import logger


class Database:
    def __init__(self, engine):
        self.engine = engine

    @contextmanager
    def connect(self):
        conn = self.engine.connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @contextmanager
    def get_raw_connection(self):
        conn = self.engine.raw_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def execute(self, query: str, params: dict = None):
        with self.connect() as conn:
            return conn.execute(text(query), params or {})
