CREATE TABLE IF NOT EXISTS audit.hr_etl_runs (
    run_id SERIAL PRIMARY KEY,
    started_at TIMESTAMP NOT NULL,
    finished_at TIMESTAMP,
    status VARCHAR(20),
    rows_extracted INTEGER,
    rows_loaded INTEGER,
    rows_rejected INTEGER DEFAULT 0,
    error_message TEXT,
    excel_file_path VARCHAR(500),
    file_hash VARCHAR(32),
    excel_modified TIMESTAMP,
    schema_version VARCHAR(20) DEFAULT '1.0'
);

CREATE INDEX IF NOT EXISTS idx_hr_etl_runs_run_id ON audit.hr_etl_runs (run_id);
