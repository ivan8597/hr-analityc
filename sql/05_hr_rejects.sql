CREATE TABLE IF NOT EXISTS staging.hr_rejects (
    reject_id BIGSERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL,
    source_row JSONB,
    column_name VARCHAR(100),
    raw_value TEXT,
    reject_reason TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_hr_rejects_run_id ON staging.hr_rejects (run_id);
CREATE INDEX IF NOT EXISTS idx_hr_rejects_reason ON staging.hr_rejects (reject_reason);
