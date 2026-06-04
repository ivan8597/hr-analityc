import hashlib
import os
from datetime import datetime

from sqlalchemy import create_engine

from ..db import Database
from ..lock import PgAdvisoryLock
from ..logger import logger
from .config import HRConfig
from .pipeline import HRPipeline
from .schema_mapper import HRSchemaMapper

HR_LOCK_ID = 987654321
SCHEMA_VERSION = "1.2"


def is_already_processed(db: Database, file_hash: str) -> bool:
    result = db.execute(
        "SELECT 1 FROM audit.hr_etl_runs "
        "WHERE file_hash = :hash AND status = 'SUCCESS' AND schema_version = :version",
        {'hash': file_hash, 'version': SCHEMA_VERSION}
    )
    return result.fetchone() is not None


def _compute_file_hash(file_path: str) -> str:
    h = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    engine = create_engine(HRConfig.DATABASE_URL, pool_size=5, max_overflow=10)
    db = Database(engine)

    if not os.path.exists(HRConfig.HR_EXCEL_PATH):
        logger.error(f"HR Excel file not found: {HRConfig.HR_EXCEL_PATH}")
        return 1

    file_hash = _compute_file_hash(HRConfig.HR_EXCEL_PATH)

    with PgAdvisoryLock(db, lock_id=HR_LOCK_ID):
        if is_already_processed(db, file_hash):
            logger.info(
                f"HR file already processed successfully "
                f"(hash={file_hash}, version={SCHEMA_VERSION}). Skipping."
            )
            return 0

        run_id = db.execute(
            "INSERT INTO audit.hr_etl_runs "
            "(started_at, status, excel_file_path, file_hash, excel_modified, schema_version) "
            "VALUES (CURRENT_TIMESTAMP, 'RUNNING', :path, :hash, :mtime, :version) RETURNING run_id",
            {
                'path': HRConfig.HR_EXCEL_PATH,
                'hash': file_hash,
                'mtime': datetime.fromtimestamp(os.path.getmtime(HRConfig.HR_EXCEL_PATH)),
                'version': SCHEMA_VERSION
            }
        ).fetchone()[0]

        try:
            mapper = HRSchemaMapper(HRConfig.HR_SCHEMA_MAPPING_PATH)
            pipeline = HRPipeline(db, mapper, run_id, HRConfig.HR_EXCEL_PATH)
            rows_extracted, rows_loaded, rows_rejected = pipeline.run()

            db.execute(
                "UPDATE audit.hr_etl_runs SET finished_at = CURRENT_TIMESTAMP, "
                "status = 'SUCCESS', rows_extracted = :extracted, rows_loaded = :loaded, "
                "rows_rejected = :rejected WHERE run_id = :run_id",
                {
                    'extracted': rows_extracted,
                    'loaded': rows_loaded,
                    'rejected': rows_rejected,
                    'run_id': run_id
                }
            )
            logger.info("HR ETL completed successfully")
            return 0
        except Exception as e:
            db.execute(
                "UPDATE audit.hr_etl_runs SET finished_at = CURRENT_TIMESTAMP, "
                "status = 'FAILED', error_message = :error WHERE run_id = :run_id",
                {'error': str(e), 'run_id': run_id}
            )
            logger.exception("HR ETL failed")
            return 1


if __name__ == '__main__':
    exit(main())
