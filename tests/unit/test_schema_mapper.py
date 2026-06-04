import pytest


def test_map_columns_exact_match(schema_mapper):
    df_cols = ["Таб. номер", "Фамилия Имя Отчество", "Дата приема"]
    mapping = schema_mapper.map_columns(df_cols)
    assert mapping["source_id"] == "Таб. номер"
    assert mapping["full_name"] == "Фамилия Имя Отчество"
    assert mapping["hire_date"] == "Дата приема"


def test_map_columns_fuzzy_match(schema_mapper):
    df_cols = ["Таб номер", "Фамилия Имя Отчество", "дата приема"]
    original = schema_mapper.threshold
    schema_mapper.threshold = 80
    mapping = schema_mapper.map_columns(df_cols)
    assert mapping["source_id"] == "Таб номер"
    assert mapping["full_name"] == "Фамилия Имя Отчество"
    assert mapping["hire_date"] == "дата приема"
    schema_mapper.threshold = original


def test_map_columns_required_missing(schema_mapper):
    df_cols = ["Фамилия Имя Отчество"]
    with pytest.raises(ValueError, match="Required HR column 'source_id' not found"):
        schema_mapper.map_columns(df_cols)


def test_map_columns_optional_missing(schema_mapper, caplog):
    df_cols = ["Таб. номер", "Фамилия Имя Отчество"]
    mapping = schema_mapper.map_columns(df_cols)
    assert "position" not in mapping
    assert "Optional HR column 'position' not found" in caplog.text
