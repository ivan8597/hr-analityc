import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from dashboard.metrics import CERT_FIELDS


def empty_figure(title: str = "Нет данных"):
    return px.bar(title=title)


def department_bar(df: pd.DataFrame, title: str = "Сотрудники по отделам (топ-15)"):
    chart_df = (
        df["department"]
        .fillna("Не указан")
        .value_counts()
        .reset_index(name="count")
        .rename(columns={"index": "department"})
        .head(15)
    )
    return px.bar(
        chart_df,
        x="count",
        y="department",
        orientation="h",
        title=title,
        labels={"count": "Кол-во", "department": "Отдел"},
    )


def gender_pie(df: pd.DataFrame):
    chart_df = (
        df["gender"]
        .fillna("Не указан")
        .value_counts()
        .reset_index(name="count")
        .rename(columns={"index": "gender"})
    )
    return px.pie(
        chart_df,
        names="gender",
        values="count",
        title="Распределение по полу",
        hole=0.35,
    )


def hire_line(df: pd.DataFrame):
    chart_df = df.dropna(subset=["hire_date"]).copy()
    if chart_df.empty:
        return empty_figure("Приёмы по годам (нет данных)")
    chart_df["year"] = chart_df["hire_date"].dt.year
    grouped = chart_df.groupby("year", as_index=False).size().rename(columns={"size": "count"})
    return px.line(
        grouped,
        x="year",
        y="count",
        markers=True,
        title="Приёмы по годам",
        labels={"year": "Год", "count": "Кол-во"},
    )


def state_bar(df: pd.DataFrame):
    chart_df = (
        df["state_norm"]
        .value_counts()
        .reset_index(name="count")
        .rename(columns={"index": "state_norm"})
    )
    return px.bar(
        chart_df,
        x="state_norm",
        y="count",
        title="Состояние сотрудников",
        labels={"state_norm": "Состояние", "count": "Кол-во"},
    )


def position_bar(df: pd.DataFrame):
    chart_df = (
        df["position"]
        .fillna("Не указано")
        .value_counts()
        .reset_index(name="count")
        .rename(columns={"index": "position"})
        .head(15)
    )
    return px.bar(
        chart_df,
        x="count",
        y="position",
        orientation="h",
        title="Top-15 должностей",
        labels={"count": "Кол-во", "position": "Должность"},
    )


def department_gender_heatmap(df: pd.DataFrame):
    chart_df = df.copy()
    chart_df["department"] = chart_df["department"].fillna("Не указан")
    chart_df["gender"] = chart_df["gender"].fillna("Не указан")
    chart_df = (
        chart_df.groupby(["department", "gender"])
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
        .head(60)
    )
    if chart_df.empty:
        return empty_figure("Heatmap отдел × пол")
    pivot = chart_df.pivot(index="department", columns="gender", values="count").fillna(0)
    return px.imshow(
        pivot,
        title="Heatmap: отдел × пол (топ-60 комбинаций)",
        labels={"x": "Пол", "y": "Отдел", "color": "Кол-во"},
        aspect="auto",
    )


def tenure_by_department(df: pd.DataFrame):
    subset = df.dropna(subset=["tenure_years"]).copy()
    subset["department"] = subset["department"].fillna("Не указан")
    chart_df = (
        subset.groupby("department", as_index=False)["tenure_years"]
        .mean()
        .sort_values("tenure_years", ascending=False)
        .head(15)
    )
    if chart_df.empty:
        return empty_figure("Средний стаж по отделам")
    return px.bar(
        chart_df,
        x="tenure_years",
        y="department",
        orientation="h",
        title="Средний стаж по отделам (топ-15)",
        labels={"tenure_years": "Средний стаж, лет", "department": "Отдел"},
    )


def harmful_by_department(df: pd.DataFrame):
    subset = df[df["harmful"] == True].copy()
    subset["department"] = subset["department"].fillna("Не указан")
    chart_df = (
        subset.groupby("department", as_index=False)
        .size()
        .rename(columns={"size": "count"})
        .sort_values("count", ascending=False)
        .head(15)
    )
    if chart_df.empty:
        return empty_figure("Вредники по отделам")
    return px.bar(
        chart_df,
        x="count",
        y="department",
        orientation="h",
        title="Вредники по отделам",
        labels={"count": "Кол-во", "department": "Отдел"},
    )


def permits_by_type(df: pd.DataFrame):
    rows = []
    mapping = {
        "height": "Высота",
        "cradle": "Люльки",
        "fire_safety": "Пожарная",
        "electrical_safety": "Элбезопасность",
        "pmk_safety": "ПМК",
        "special_assessment": "Спецоценка",
    }
    for field, label in mapping.items():
        if field in df.columns:
            rows.append({"type": label, "count": int(df[field].notna().sum())})
    chart_df = pd.DataFrame(rows)
    if chart_df.empty:
        return empty_figure("Допуски по типам")
    return px.bar(
        chart_df,
        x="type",
        y="count",
        title="Заполненность допусков по типам",
        labels={"type": "Тип", "count": "Кол-во записей"},
    )


def cert_status_chart(df: pd.DataFrame):
    rows = []
    for field in CERT_FIELDS:
        col = f"{field}_status"
        if col not in df.columns:
            continue
        counts = df[col].value_counts()
        for status, count in counts.items():
            rows.append({"cert_type": field, "status": status, "count": int(count)})
    chart_df = pd.DataFrame(rows)
    if chart_df.empty:
        return empty_figure("Статус аттестаций")
    return px.bar(
        chart_df,
        x="cert_type",
        y="count",
        color="status",
        barmode="stack",
        title="Статус аттестаций по типам",
        labels={"cert_type": "Тип", "count": "Кол-во", "status": "Статус"},
    )


def overdue_heatmap(df: pd.DataFrame):
    rows = []
    for field in CERT_FIELDS:
        col = f"{field}_status"
        if col not in df.columns:
            continue
        grouped = (
            df.assign(department=df["department"].fillna("Не указан"))
            .groupby(["department", col], as_index=False)
            .size()
            .rename(columns={"size": "count", col: "status"})
        )
        overdue = grouped[grouped["status"].isin(["Просрочено", "Истекает скоро"])]
        for _, row in overdue.iterrows():
            rows.append(
                {
                    "department": row["department"],
                    "cert_type": field,
                    "count": row["count"],
                }
            )
    chart_df = pd.DataFrame(rows)
    if chart_df.empty:
        return empty_figure("Просрочки по отделам")
    pivot = chart_df.pivot_table(
        index="department",
        columns="cert_type",
        values="count",
        aggfunc="sum",
        fill_value=0,
    )
    return px.imshow(
        pivot,
        title="Просрочки и скорое истечение по отделам",
        labels={"x": "Тип аттестации", "y": "Отдел", "color": "Кол-во"},
        aspect="auto",
    )


def fill_rate_chart(fill_rates: list[dict]):
    chart_df = pd.DataFrame(fill_rates)
    if chart_df.empty:
        return empty_figure("Заполненность полей")
    return px.bar(
        chart_df,
        x="fill_pct",
        y="field",
        orientation="h",
        title="Заполненность полей, %",
        labels={"fill_pct": "%", "field": "Поле"},
    )


def rejects_chart(rejects: pd.DataFrame):
    if rejects.empty:
        return empty_figure("Причины reject")
    return px.bar(
        rejects,
        x="reject_count",
        y="reject_reason",
        orientation="h",
        title="Причины reject (топ-15)",
        labels={"reject_count": "Кол-во", "reject_reason": "Причина"},
    )
