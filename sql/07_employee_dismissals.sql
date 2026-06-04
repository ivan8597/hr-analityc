ALTER TABLE core.hr_employee
    ADD COLUMN IF NOT EXISTS is_dismissed BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS dismissed_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS last_seen_run_id INTEGER;

CREATE INDEX IF NOT EXISTS idx_hr_employee_is_dismissed
    ON core.hr_employee(is_dismissed);
