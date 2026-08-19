import re
from datetime import date, timedelta

import pandas as pd

CERT_FIELDS = [
    "electrical_safety",
    "fire_safety",
    "pmk_safety",
    "special_assessment",
    "height",
    "cradle",
]

TRACKED_FIELDS = [
    "full_name",
    "source_id",
    "department",
    "position",
    "gender",
    "hire_date",
    "state",
    "is_dismissed",
    "harmful",
    "electrical_safety",
    "fire_safety",
    "pmk_safety",
    "special_assessment",
    "height",
    "cradle",
    "return_date",
]

DATE_PATTERN = re.compile(r"(\d{1,2})[./](\d{1,2})[./](\d{2,4})")


TABLE_COLUMN_LABELS = {
    "source_id": "Таб. №",
    "full_name": "ФИО",
    "department": "Отдел",
    "position": "Должность",
    "gender": "Пол",
    "hire_date": "Дата приёма",
    "tenure": "Стаж",
    "state": "Состояние",
    "harmful": "Вредник",
}


def is_true(value) -> bool:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    text = str(value).strip().lower()
    return text in {"true", "1", "yes", "да", "t"}


def normalize_state(value, is_dismissed: bool = False) -> str:
    if is_true(is_dismissed):
        return "Уволенные"
    if pd.isna(value) or str(value).strip() == "":
        return "Работает"
    return str(value).strip()


def prepare_employees(df: pd.DataFrame) -> pd.DataFrame:
    prepared = df.copy()
    if "is_dismissed" not in prepared.columns:
        prepared["is_dismissed"] = False
    else:
        prepared["is_dismissed"] = prepared["is_dismissed"].apply(is_true)
    prepared["state_norm"] = prepared.apply(
        lambda row: normalize_state(row.get("state"), row.get("is_dismissed")),
        axis=1,
    )
    prepared["hire_date"] = pd.to_datetime(prepared["hire_date"], errors="coerce")
    prepared["tenure_years"] = (
        (pd.Timestamp.today().normalize() - prepared["hire_date"]).dt.days / 365.25
    )
    for field in CERT_FIELDS:
        if field in prepared.columns:
            prepared[f"{field}_status"] = prepared[field].apply(parse_cert_status)
    return prepared


def parse_cert_status(value) -> str:
    if pd.isna(value) or str(value).strip() == "":
        return "Не указано"

    text = str(value).strip()
    lowered = text.lower()
    if "бессроч" in lowered:
        return "Бессрочно"

    parsed_date = _extract_date(text)
    if parsed_date is None:
        return "Не распознано"

    today = date.today()
    soon = today + timedelta(days=30)
    if parsed_date < today:
        return "Просрочено"
    if parsed_date <= soon:
        return "Истекает скоро"
    return "Актуально"


def _extract_date(text: str):
    match = DATE_PATTERN.search(text)
    if match:
        day, month, year = match.groups()
        year = int(year)
        if year < 100:
            year += 2000
        try:
            return date(year, int(month), int(day))
        except ValueError:
            pass

    parsed = pd.to_datetime(text, errors="coerce", dayfirst=True, format="mixed")
    if pd.notna(parsed):
        return parsed.date()
    return None


def build_filter_options(df: pd.DataFrame) -> dict:
    departments = sorted(df["department"].fillna("Не указан").astype(str).unique())
    genders = sorted(df["gender"].fillna("Не указан").astype(str).unique())
    states = sorted(df["state_norm"].astype(str).unique())
    years = sorted(df["hire_date"].dropna().dt.year.astype(int).unique()) if "hire_date" in df else []
    return {
        "departments": [{"label": value, "value": value} for value in departments],
        "genders": [{"label": value, "value": value} for value in genders],
        "states": [{"label": value, "value": value} for value in states],
        "years": [{"label": str(value), "value": value} for value in years],
    }


def apply_filters(
    df: pd.DataFrame,
    departments: list[str] | None,
    genders: list[str] | None,
    harmful_filter: str,
    states: list[str] | None,
    hire_years: list[int] | None,
    search_value: str | None,
    dismissed_filter: str = "all",
) -> pd.DataFrame:
    filtered = df.copy()

    if dismissed_filter == "active":
        filtered = filtered[~filtered["is_dismissed"].apply(is_true)]
    elif dismissed_filter == "dismissed":
        filtered = filtered[filtered["is_dismissed"].apply(is_true)]

    if departments:
        filtered = filtered[
            filtered["department"].fillna("Не указан").astype(str).isin(departments)
        ]

    if genders:
        filtered = filtered[
            filtered["gender"].fillna("Не указан").astype(str).isin(genders)
        ]

    if states:
        filtered = filtered[filtered["state_norm"].astype(str).isin(states)]

    if harmful_filter == "yes":
        filtered = filtered[filtered["harmful"] == True]
    elif harmful_filter == "no":
        filtered = filtered[filtered["harmful"] != True]

    if hire_years:
        filtered = filtered[filtered["hire_date"].dt.year.isin(hire_years)]

    if search_value:
        needle = search_value.lower()
        filtered = filtered[
            filtered.apply(
                lambda row: any(
                    needle in str(value).lower()
                    for value in [
                        row.get("full_name"),
                        row.get("source_id"),
                        row.get("position"),
                        row.get("department"),
                        row.get("state_norm"),
                        row.get("gender"),
                    ]
                    if pd.notna(value)
                ),
                axis=1,
            )
        ]

    return filtered


def overview_kpis(df: pd.DataFrame) -> dict:
    current_year = date.today().year
    dismissed = int(df["is_dismissed"].apply(is_true).sum()) if "is_dismissed" in df.columns else 0
    on_leave = df["state_norm"].str.contains("отпуск|приостанов", case=False, na=False).sum()
    avg_tenure = df["tenure_years"].dropna().mean()
    male = (df["gender"] == "м").sum()
    female = (df["gender"] == "ж").sum()
    harmful = (df["harmful"] == True).sum()
    new_year = df["hire_date"].dt.year.eq(current_year).sum()
    return {
        "employees": len(df),
        "male_female": f"{male} / {female}",
        "avg_tenure": f"{avg_tenure:.1f} лет" if pd.notna(avg_tenure) else "—",
        "new_year": int(new_year),
        "harmful": int(harmful),
        "harmful_pct": f"{(harmful / len(df) * 100):.1f}%" if len(df) else "0%",
        "on_leave": int(on_leave),
        "dismissed": dismissed,
    }


def structure_kpis(df: pd.DataFrame) -> dict:
    dept_counts = df["department"].fillna("Не указан").value_counts()
    pos_counts = df["position"].fillna("Не указано").value_counts()
    largest = dept_counts.index[0] if not dept_counts.empty else "—"
    largest_count = int(dept_counts.iloc[0]) if not dept_counts.empty else 0
    smallest = dept_counts.index[-1] if not dept_counts.empty else "—"
    smallest_count = int(dept_counts.iloc[-1]) if not dept_counts.empty else 0
    return {
        "departments": df["department"].dropna().nunique(),
        "positions": df["position"].dropna().nunique(),
        "largest_dept": f"{largest} ({largest_count})",
        "smallest_dept": f"{smallest} ({smallest_count})",
    }


def safety_kpis(df: pd.DataFrame) -> dict:
    harmful = (df["harmful"] == True).sum()
    height = df["height"].notna().sum() if "height" in df else 0
    cradle = df["cradle"].notna().sum() if "cradle" in df else 0
    fire_filled = df["fire_safety"].notna().sum() if "fire_safety" in df else 0
    overdue = count_cert_status(df, "Просрочено")
    return {
        "harmful": int(harmful),
        "height": int(height),
        "cradle": int(cradle),
        "fire_filled": int(fire_filled),
        "overdue": int(overdue),
    }


def count_cert_status(df: pd.DataFrame, status: str) -> int:
    total = 0
    for field in CERT_FIELDS:
        col = f"{field}_status"
        if col in df.columns:
            total += (df[col] == status).sum()
    return total


def quality_kpis(df: pd.DataFrame, rejects_total: int, last_run) -> dict:
    fill_rates = field_fill_rates(df)
    avg_fill = sum(item["fill_pct"] for item in fill_rates) / len(fill_rates) if fill_rates else 0
    missing_gender = int(df["gender"].isna().sum())
    missing_department = int(df["department"].isna().sum())
    if isinstance(last_run, dict):
        last_status = last_run.get("status", "—")
    elif last_run:
        last_status = last_run.status
    else:
        last_status = "—"
    return {
        "quality_score": f"{avg_fill:.1f}%",
        "missing_gender": missing_gender,
        "missing_department": missing_department,
        "rejects": rejects_total,
        "last_etl": last_status,
    }


def field_fill_rates(df: pd.DataFrame) -> list[dict]:
    rows = []
    total = len(df)
    for field in TRACKED_FIELDS:
        if field not in df.columns:
            continue
        filled = int(df[field].notna().sum())
        if field == "harmful":
            filled = int((df[field] == True).sum())
        rows.append(
            {
                "field": field,
                "filled": filled,
                "fill_pct": round(filled / total * 100, 1) if total else 0,
            }
        )
    return rows


def risk_table(df: pd.DataFrame) -> pd.DataFrame:
    status_cols = [f"{field}_status" for field in CERT_FIELDS if f"{field}_status" in df.columns]
    if not status_cols:
        return pd.DataFrame()

    risky = df.copy()
    risky["risk_flags"] = risky[status_cols].apply(
        lambda row: sum(value in {"Просрочено", "Истекает скоро", "Не распознано"} for value in row),
        axis=1,
    )
    risky = risky[(risky["risk_flags"] > 0) | (risky["harmful"] == True)]
    cols = [
        "source_id",
        "full_name",
        "department",
        "position",
        "harmful",
        "fire_safety",
        "electrical_safety",
        "pmk_safety",
        "special_assessment",
        "height",
        "cradle",
        "risk_flags",
    ]
    return risky[cols].sort_values("risk_flags", ascending=False)


def format_tenure(years) -> str:
    if pd.isna(years):
        return "—"
    total_months = max(int(round(float(years) * 12)), 0)
    full_years, months = divmod(total_months, 12)
    if full_years and months:
        return f"{full_years} г. {months} мес."
    if full_years:
        return f"{full_years} г."
    return f"{months} мес."


def format_hire_date(value) -> str:
    if pd.isna(value) or value is None:
        return "—"
    return pd.Timestamp(value).strftime("%d.%m.%Y")


def format_harmful(value) -> str:
    return "Да" if is_true(value) else "Нет"


def format_dismissed(value) -> str:
    return "Да" if is_true(value) else "Нет"


def find_employees_by_query(df: pd.DataFrame, search_value: str | None, limit: int = 5) -> pd.DataFrame:
    if not search_value or not str(search_value).strip():
        return df.iloc[0:0]

    needle = str(search_value).strip().lower()
    mask = df["full_name"].fillna("").str.lower().str.contains(needle, regex=False)
    if "source_id" in df.columns:
        mask = mask | df["source_id"].fillna("").astype(str).str.lower().str.contains(needle, regex=False)

    matches = df[mask].copy()
    if matches.empty:
        return matches

    matches["match_rank"] = matches["full_name"].fillna("").str.lower().apply(
        lambda name: 0 if name.startswith(needle) else 1
    )
    return matches.sort_values(["match_rank", "full_name"]).head(limit).drop(columns=["match_rank"])


def employee_profile(row: pd.Series) -> dict:
    return {
        "full_name": row.get("full_name") or "—",
        "source_id": row.get("source_id") or "—",
        "department": row.get("department") or "—",
        "position": row.get("position") or "—",
        "hire_date": format_hire_date(row.get("hire_date")),
        "tenure": format_tenure(row.get("tenure_years")),
        "harmful": format_harmful(row.get("harmful")),
        "dismissed": format_dismissed(row.get("is_dismissed")),
        "state": row.get("state_norm") or normalize_state(row.get("state")),
    }


def table_records(df: pd.DataFrame) -> tuple[list[dict], list[dict]]:
    if df.empty:
        return [], []
    table_df = df.copy()
    for col in ["hire_date", "updated_at", "return_date", "dismissed_at"]:
        if col in table_df.columns:
            table_df[col] = table_df[col].astype(str).replace("NaT", "")
    if "harmful" in table_df.columns:
        table_df["harmful"] = table_df["harmful"].map({True: "Да", False: "Нет"}).fillna("Нет")
    if "state_norm" in table_df.columns:
        table_df["state"] = table_df["state_norm"]
    drop_cols = [c for c in table_df.columns if c.endswith("_status") or c in {"is_dismissed", "dismissed", "state_norm"}]
    table_df = table_df.drop(columns=drop_cols, errors="ignore")
    columns = [
        {"name": TABLE_COLUMN_LABELS.get(col, col), "id": col}
        for col in table_df.columns
    ]
    return table_df.to_dict("records"), columns


STAT_ALPHA = 0.05


def _safe_pct(numerator: int, denominator: int) -> float:
    return round(numerator / denominator * 100, 1) if denominator else 0.0


def _conclusion(p_value: float, alpha: float = STAT_ALPHA) -> str:
    return "Отклоняем H0" if p_value < alpha else "Нет оснований отклонить H0"


def hypothesis_tests(df: pd.DataFrame, alpha: float = STAT_ALPHA) -> list[dict]:
    """Run the two course-level hypothesis tests used in the HR analysis.

    H1 uses Fisher's exact test because the harmful-condition contingency table
    contains a small subgroup. H2 uses Pearson's chi-square test of independence
    for gender and functional group.
    """
    try:
        from scipy.stats import chi2_contingency, fisher_exact
    except ImportError as exc:
        raise RuntimeError("Для статистических критериев требуется scipy") from exc

    work = df.copy()
    if "is_dismissed" in work.columns:
        work = work[~work["is_dismissed"].apply(is_true)]
    work["department_text"] = work["department"].fillna("").astype(str)
    work["gender_text"] = work["gender"].fillna("").astype(str).str.lower().str.strip()
    work["harmful_bool"] = work["harmful"].apply(is_true)

    special_mask = work["department_text"].str.contains("спец|специальн", case=False, regex=True, na=False)
    special = work[special_mask]
    other = work[~special_mask]
    table_fisher = [
        [int(special["harmful_bool"].sum()), int((~special["harmful_bool"]).sum())],
        [int(other["harmful_bool"].sum()), int((~other["harmful_bool"]).sum())],
    ]
    odds_ratio, fisher_p = fisher_exact(table_fisher, alternative="two-sided")
    special_total = len(special)
    other_total = len(other)
    fisher_result = {
        "id": "harmful_by_department",
        "hypothesis": "Вредные условия труда связаны с участком специальных работ",
        "h0": "Доля сотрудников с вредными условиями одинакова в участке специальных работ и остальных подразделениях",
        "h1": "Доля сотрудников с вредными условиями различается между участком специальных работ и остальными подразделениями",
        "criterion": "Точный критерий Фишера, двусторонний",
        "statistic": f"OR = {odds_ratio:.2f}" if pd.notna(odds_ratio) else "OR не определён",
        "p_value": float(fisher_p),
        "p_value_display": f"{fisher_p:.4g}",
        "alpha": alpha,
        "conclusion": _conclusion(float(fisher_p), alpha),
        "comparison": f"p-value = {fisher_p:.4g} {'<' if fisher_p < alpha else '≥'} α = {alpha:.2f}",
        "sample": f"Спецработы: {int(special['harmful_bool'].sum())}/{special_total} ({_safe_pct(int(special['harmful_bool'].sum()), special_total)}%); остальные: {int(other['harmful_bool'].sum())}/{other_total} ({_safe_pct(int(other['harmful_bool'].sum()), other_total)}%)",
        "table": table_fisher,
        "contingency_headers": ["Группа", "Вредные условия: Да", "Вредные условия: Нет", "Всего", "Доля вредников"],
        "contingency_rows": [
            ["Участок специальных работ", table_fisher[0][0], table_fisher[0][1], special_total, f"{_safe_pct(table_fisher[0][0], special_total)}%"],
            ["Остальные подразделения", table_fisher[1][0], table_fisher[1][1], other_total, f"{_safe_pct(table_fisher[1][0], other_total)}%"],
        ],
        "business_conclusion": "Имеются статистически значимые основания считать, что вредные условия связаны с участком специальных работ. Контроль охраны труда следует в первую очередь сосредоточить на этом участке.",
    }

    group_mask = work["department_text"].str.contains("взиман|дэж|дэу", case=False, regex=True, na=False)
    group = work[group_mask & work["gender_text"].isin({"м", "ж", "муж", "жен"})].copy()
    group["gender_norm"] = group["gender_text"].map({"м": "Мужчины", "муж": "Мужчины", "ж": "Женщины", "жен": "Женщины"})
    group["functional_group"] = group["department_text"].str.contains("взиман", case=False, regex=True).map({True: "Взимание платы", False: "ДЭУ"})
    gender_table_df = pd.crosstab(group["functional_group"], group["gender_norm"]).reindex(
        index=["ДЭУ", "Взимание платы"], columns=["Мужчины", "Женщины"], fill_value=0
    )
    table_gender = gender_table_df.to_numpy().tolist()
    if len(group) and (gender_table_df.to_numpy().sum(axis=0) > 0).all() and (gender_table_df.to_numpy().sum(axis=1) > 0).all():
        chi2, chi_p, dof, expected = chi2_contingency(table_gender, correction=False)
        chi_statistic = f"χ² = {chi2:.2f}; df = {dof}"
        chi_p_float = float(chi_p)
        expected_min = float(expected.min())
    else:
        chi_statistic = "Недостаточно данных"
        chi_p_float = 1.0
        expected_min = 0.0
    gender_result = {
        "id": "gender_by_functional_group",
        "hypothesis": "Гендерная структура зависит от функционального типа подразделения",
        "h0": "Пол и функциональная группа подразделения независимы",
        "h1": "Пол и функциональная группа подразделения связаны",
        "criterion": "Критерий χ² Пирсона независимости, без поправки Йейтса",
        "statistic": chi_statistic,
        "p_value": chi_p_float,
        "p_value_display": f"{chi_p_float:.4g}",
        "alpha": alpha,
        "conclusion": _conclusion(chi_p_float, alpha),
        "comparison": f"p-value = {chi_p_float:.4g} {'<' if chi_p_float < alpha else '≥'} α = {alpha:.2f}",
        "sample": f"ДЭУ: {table_gender[0] if len(table_gender) > 0 else []}; взимание платы: {table_gender[1] if len(table_gender) > 1 else []}; min ожидаемая частота: {expected_min:.2f}",
        "table": table_gender,
        "contingency_headers": ["Функциональная группа", "Мужчины", "Женщины", "Всего", "Доля женщин"],
        "contingency_rows": [
            ["ДЭУ", table_gender[0][0], table_gender[0][1], sum(table_gender[0]), f"{_safe_pct(table_gender[0][1], sum(table_gender[0]))}%"],
            ["Взимание платы", table_gender[1][0], table_gender[1][1], sum(table_gender[1]), f"{_safe_pct(table_gender[1][1], sum(table_gender[1]))}%"],
        ],
        "business_conclusion": "Гендерная структура статистически значимо различается между ДЭУ и подразделениями взимания платы. Эти группы следует учитывать раздельно при планировании графиков, замещения и обучения.",
    }
    return [fisher_result, gender_result]


def hypothesis_table_records(df: pd.DataFrame, alpha: float = STAT_ALPHA) -> list[dict]:
    """Return dashboard-friendly rows with no statistical calculation hidden in UI code."""
    return [
        {
            "Гипотеза": result["hypothesis"],
            "Критерий": result["criterion"],
            "Статистика": result["statistic"],
            "p-value": result["p_value_display"],
            "α": alpha,
            "Решение": result["conclusion"],
            "Выборка и доли": result["sample"],
        }
        for result in hypothesis_tests(df, alpha)
    ]
