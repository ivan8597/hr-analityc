CREATE TABLE IF NOT EXISTS core.hr_employee (
    hr_employee_id SERIAL PRIMARY KEY,
    source_id VARCHAR(50) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    responsible VARCHAR(255),
    position VARCHAR(255),
    department VARCHAR(255),
    hire_date DATE,
    state VARCHAR(100),
    electrical_safety TEXT,
    return_date DATE,
    height VARCHAR(50),
    cradle VARCHAR(50),
    harmful BOOLEAN,
    fire_safety TEXT,
    pmk_safety TEXT,
    special_assessment TEXT,
    gender VARCHAR(20),
    is_dismissed BOOLEAN NOT NULL DEFAULT FALSE,
    dismissed_at TIMESTAMP,
    last_seen_run_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_hr_employee_source_id ON core.hr_employee(source_id);
CREATE INDEX IF NOT EXISTS idx_hr_employee_full_name ON core.hr_employee(full_name);
CREATE INDEX IF NOT EXISTS idx_hr_employee_is_dismissed ON core.hr_employee(is_dismissed);
