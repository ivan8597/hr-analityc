import pandas as pd

from dashboard.metrics import hypothesis_tests


def _frame(special_harmful, special_total, other_harmful, other_total):
    rows = []
    for index in range(special_total):
        rows.append({
            "department": "Участок специальных работ",
            "harmful": index < special_harmful,
            "gender": "м",
            "is_dismissed": False,
        })
    for index in range(other_total):
        rows.append({
            "department": "ДЭУ",
            "harmful": index < other_harmful,
            "gender": "м" if index < other_total * 0.9 else "ж",
            "is_dismissed": False,
        })
    return pd.DataFrame(rows)


def test_fisher_test_detects_concentration_of_harmful_conditions():
    results = hypothesis_tests(_frame(9, 13, 8, 700))
    result = results[0]

    assert result["criterion"].startswith("Точный критерий Фишера")
    assert result["p_value"] < 0.05
    assert result["conclusion"] == "Отклоняем H0"
    assert result["table"] == [[9, 4], [8, 692]]


def test_chi_square_test_detects_gender_difference_between_groups():
    rows = (
        [{"department": "Отдел взимания платы", "harmful": False, "gender": "ж", "is_dismissed": False} for _ in range(20)]
        + [{"department": "ДЭУ", "harmful": False, "gender": "м", "is_dismissed": False} for _ in range(20)]
    )
    results = hypothesis_tests(pd.DataFrame(rows))
    result = results[1]

    assert result["criterion"].startswith("Критерий χ²")
    assert result["p_value"] < 0.05
    assert result["conclusion"] == "Отклоняем H0"
    assert result["statistic"].startswith("χ² = ")
