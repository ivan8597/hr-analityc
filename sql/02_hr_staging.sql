CREATE TABLE IF NOT EXISTS staging.hr_raw (
    run_id INTEGER NOT NULL,
    row_id INTEGER NOT NULL,
    source_id VARCHAR(50),
    full_name VARCHAR(255),
    responsible VARCHAR(255),
    position VARCHAR(255),
    department VARCHAR(255),
    hire_date TEXT,
    state VARCHAR(100),
    electrical_safety TEXT,
    return_date TEXT,
    height VARCHAR(50),
    cradle VARCHAR(50),
    harmful TEXT,
    fire_safety TEXT,
    pmk_safety TEXT,
    special_assessment TEXT,
    gender VARCHAR(20),
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT hr_raw_run_id_not_null CHECK (run_id IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_hr_raw_run_id ON staging.hr_raw (run_id);
CREATE INDEX IF NOT EXISTS idx_hr_raw_source_id ON staging.hr_raw (source_id);
