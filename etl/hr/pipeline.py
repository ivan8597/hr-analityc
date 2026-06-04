import hashlib
import os
from datetime import datetime

from ..db import Database
from ..logger import logger
from .extract import extract
from .reject_logger import RejectLogger
from .repository import HRRepository
from .schema_mapper import HRSchemaMapper
from .transform import transform


class HRPipeline:
    def __init__(self, db: Database, mapper: HRSchemaMapper, run_id: int, file_path: str):
        self.db = db
        self.mapper = mapper
        self.repo = HRRepository(db)
        self.run_id = run_id
        self.file_path = file_path
        self.file_hash = self._get_file_hash()
        self.file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
        self.reject_logger = RejectLogger(db, run_id)

    def _get_file_hash(self) -> str:
        h = hashlib.md5()
        with open(self.file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                h.update(chunk)
        return h.hexdigest()

    def run(self) -> tuple[int, int, int]:
        logger.info(f"Starting HR ETL pipeline run {self.run_id}")

        raw_df = extract(self.mapper, reject_logger=self.reject_logger, excel_path=self.file_path)
        rows_extracted = len(raw_df)

        self.repo.insert_staging(raw_df, self.run_id, self.file_hash, self.file_mtime)

        transformed_df = transform(raw_df, reject_logger=self.reject_logger)
        rows_loaded = len(transformed_df)

        self.repo.upsert_employees(transformed_df, self.run_id)
        self.repo.mark_missing_as_dismissed(
            transformed_df['source_id'].dropna().astype(str).tolist(),
            self.run_id
        )

        self.reject_logger.flush()

        res = self.db.execute(
            "SELECT COUNT(*) FROM staging.hr_rejects WHERE run_id = :run_id",
            {'run_id': self.run_id}
        )
        rows_rejected = res.fetchone()[0]

        logger.info(
            f"HR ETL run {self.run_id}: extracted={rows_extracted}, "
            f"loaded={rows_loaded}, rejected={rows_rejected}"
        )
        return rows_extracted, rows_loaded, rows_rejected
