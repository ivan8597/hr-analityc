import pandas as pd
from unittest.mock import Mock

from etl.hr.transform import transform


def test_transform_cleans_dates():
    df = pd.DataFrame({
        "source_id": ["001", "002", "003"],
        "full_name": ["Иванов", "Петров", "Сидоров"],
        "hire_date": ["2023-01-15", "invalid", None],
    })
    transformed = transform(df)
    assert transformed["hire_date"].iloc[0] == pd.Timestamp("2023-01-15").date()
    assert pd.isna(transformed["hire_date"].iloc[1])
    assert pd.isna(transformed["hire_date"].iloc[2])


def test_transform_removes_duplicates():
    df = pd.DataFrame({
        "source_id": ["001", "001", "002"],
        "full_name": ["Иванов", "Иванов Иван", "Петров"],
    })
    transformed = transform(df)
    assert len(transformed) == 2
    assert transformed["source_id"].tolist() == ["001", "002"]
    assert transformed.loc[transformed["source_id"] == "001", "full_name"].iloc[0] == "Иванов Иван"


def test_transform_removes_rows_with_missing_required():
    df = pd.DataFrame({
        "source_id": ["001", None, "003"],
        "full_name": ["Иванов", "Петров", None],
    })
    transformed = transform(df)
    assert len(transformed) == 1
    assert transformed.iloc[0]["source_id"] == "001"


def test_transform_logs_rejects_for_dates():
    reject_logger = Mock()
    df = pd.DataFrame({
        "source_id": ["001"],
        "full_name": ["Иванов"],
        "hire_date": ["bad_date"],
    })
    transform(df, reject_logger=reject_logger)
    reject_logger.log_reject.assert_called_once()
    _, kwargs = reject_logger.log_reject.call_args
    assert kwargs["column_name"] == "hire_date"
    assert "Invalid date format" in kwargs["reason"]


def test_transform_harmful_field():
    df = pd.DataFrame({
        "source_id": ["001"],
        "full_name": ["Иванов"],
        "harmful": [True],
    })
    transformed = transform(df)
    assert bool(transformed["harmful"].iloc[0]) is True

    df2 = pd.DataFrame({
        "source_id": ["002"],
        "full_name": ["Петров"],
    })
    transformed2 = transform(df2)
    assert bool(transformed2["harmful"].iloc[0]) is False
