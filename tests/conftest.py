import json
import os
import tempfile
from pathlib import Path

os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")

import pandas as pd
import pytest
from sqlalchemy import create_engine, text
from testcontainers.postgres import PostgresContainer

from etl.db import Database
from etl.hr.schema_mapper import HRSchemaMapper

PROJECT_ROOT = Path(__file__).parent.parent


def _apply_sql_schemas(engine):
    sql_files = [
        "01_schema.sql",
        "02_hr_staging.sql",
        "03_hr_audit.sql",
        "04_hr_core.sql",
        "05_hr_rejects.sql",
    ]
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS staging CASCADE"))
        conn.execute(text("DROP SCHEMA IF EXISTS core CASCADE"))
        conn.execute(text("DROP SCHEMA IF EXISTS audit CASCADE"))
        conn.commit()
        for fname in sql_files:
            sql_path = PROJECT_ROOT / "sql" / fname
            with open(sql_path, "r", encoding="utf-8") as f:
                sql_script = f.read()
            for statement in sql_script.split(";"):
                if statement.strip():
                    conn.execute(text(statement))
        conn.commit()


def _truncate_tables(engine):
    with engine.connect() as conn:
        conn.execute(text(
            "TRUNCATE staging.hr_raw, staging.hr_rejects, "
            "core.hr_employee, audit.hr_etl_runs RESTART IDENTITY CASCADE"
        ))
        conn.commit()


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:15") as postgres:
        yield postgres


@pytest.fixture(scope="function")
def pg_db(postgres_container):
    engine = create_engine(postgres_container.get_connection_url())
    db = Database(engine)
    _apply_sql_schemas(engine)
    yield db
    _truncate_tables(engine)


@pytest.fixture
def clean_tables(pg_db):
    _truncate_tables(pg_db.engine)
    return pg_db


@pytest.fixture
def test_excel_file():
    df = pd.DataFrame({
        "Таб. номер": ["001", "002", "003", "004"],
        "Фамилия Имя Отчество": [
            "Иванов Иван Иванович",
            "Петров Петр Петрович",
            "Сидорова Анна Сергеевна",
            None,
        ],
        "Должность по штатному расписанию": ["Инженер", "Техник", None, "Менеджер"],
        "Дата приема": ["2023-01-15", "invalid_date", "2023-03-20", ""],
        "Вредники": [True, False, None, True],
        "Состояние": ["Активен", "Уволен", "Активен", "Активен"],
    })
    fd, path = tempfile.mkstemp(suffix=".xlsx")
    os.close(fd)
    df.to_excel(path, index=False)
    yield path
    os.unlink(path)


@pytest.fixture
def test_mapping_content():
    return {
        "columns": {
            "source_id": {"patterns": ["Таб. номер"], "required": True},
            "full_name": {"patterns": ["Фамилия Имя Отчество"], "required": True},
            "position": {"patterns": ["Должность по штатному расписанию"], "required": False},
            "hire_date": {"patterns": ["Дата приема"], "required": False},
            "harmful": {"patterns": ["Вредники"], "required": False},
            "state": {"patterns": ["Состояние"], "required": False},
        }
    }


@pytest.fixture
def test_mapping_file(test_mapping_content):
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(test_mapping_content, f)
    yield path
    os.unlink(path)


@pytest.fixture
def schema_mapper(test_mapping_file):
    return HRSchemaMapper(test_mapping_file)


@pytest.fixture
def run_id(pg_db):
    result = pg_db.execute(
        "INSERT INTO audit.hr_etl_runs (started_at, status) "
        "VALUES (CURRENT_TIMESTAMP, 'TESTING') RETURNING run_id"
    )
    return result.fetchone()[0]
