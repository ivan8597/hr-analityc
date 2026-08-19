import os
from datetime import date

import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, dash_table, dcc, html

from dashboard import charts
from dashboard.data import load_employees, load_etl_runs, load_last_run, load_reject_summary
from dashboard.metrics import (
    apply_filters,
    build_filter_options,
    employee_profile,
    field_fill_rates,
    find_employees_by_query,
    format_hire_date,
    format_tenure,
    overview_kpis,
    hypothesis_tests,
    prepare_employees,
    quality_kpis,
    risk_table,
    safety_kpis,
    structure_kpis,
    table_records,
)

DASH_HOST = os.getenv("DASH_HOST", "127.0.0.1")
DASH_PORT = int(os.getenv("DASH_PORT", "8050"))
DASH_DEBUG = os.getenv("DASH_DEBUG", "false").lower() == "true"


def _kpi_row(items: list[tuple[str, str, str]]) -> dbc.Row:
    cols = []
    width = 12 // max(len(items), 1)
    for title, value, subtitle in items:
        cols.append(
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.Div(title, className="text-muted small"),
                            html.H4(str(value), className="mb-0"),
                            html.Div(subtitle, className="text-muted small mt-1"),
                        ]
                    ),
                    className="h-100 shadow-sm",
                ),
                md=max(width, 2),
                sm=6,
                xs=12,
            )
        )
    return dbc.Row(cols, className="g-3 mb-4")


def _hypothesis_card(result: dict, number: int):
    decision_color = "success" if result["p_value"] < result["alpha"] else "warning"
    return dbc.Card(
        dbc.CardBody(
            [
                html.H5(f"Гипотеза {number}. {result['hypothesis']}", className="mb-3"),
                html.Div([html.Strong("H0: "), result["h0"]], className="mb-2"),
                html.Div([html.Strong("H1: "), result["h1"]], className="mb-3"),
                dbc.Alert([html.Strong("Выбор статистического критерия: "), result["criterion"]], color="light", className="mb-3"),
                html.H6("Таблица сопряжённости", className="mt-2"),
                dbc.Table.from_dataframe(
                    pd.DataFrame(result["contingency_rows"], columns=result["contingency_headers"]),
                    striped=True,
                    bordered=True,
                    hover=True,
                    size="sm",
                    className="mb-3",
                ),
                dbc.Row(
                    [
                        dbc.Col([html.Div("Расчёт статистики", className="text-muted small"), html.Strong(result["statistic"])], md=3, xs=12),
                        dbc.Col([html.Div("p-value", className="text-muted small"), html.Strong(result["p_value_display"])], md=2, xs=12),
                        dbc.Col([html.Div("Уровень значимости", className="text-muted small"), html.Strong(f"α = {result['alpha']:.2f}")], md=2, xs=12),
                        dbc.Col([html.Div("Сравнение", className="text-muted small"), html.Strong(result["comparison"])], md=5, xs=12),
                    ],
                    className="g-3 mb-3",
                ),
                dbc.Alert(
                    [html.Strong(f"Решение по H0: {result['conclusion']}. "), result["business_conclusion"]],
                    color=decision_color,
                    className="mb-0",
                ),
            ]
        ),
        className="shadow-sm mb-4",
    )


def _filters_card() -> dbc.Card:
    return dbc.Card(
        dbc.CardBody(
            [
                html.H5("Фильтры", className="mb-3"),
                dbc.Row(
                    [
                        dbc.Col(
                            [html.Label("Отдел"), dcc.Dropdown(id="department-filter", multi=True, placeholder="Все отделы")],
                            md=3,
                            xs=12,
                        ),
                        dbc.Col(
                            [html.Label("Пол"), dcc.Dropdown(id="gender-filter", multi=True, placeholder="Все")],
                            md=2,
                            xs=12,
                        ),
                        dbc.Col(
                            [
                                html.Label("Вредники"),
                                dcc.Dropdown(
                                    id="harmful-filter",
                                    options=[
                                        {"label": "Все", "value": "all"},
                                        {"label": "Да", "value": "yes"},
                                        {"label": "Нет", "value": "no"},
                                    ],
                                    value="all",
                                    clearable=False,
                                ),
                            ],
                            md=2,
                            xs=12,
                        ),
                        dbc.Col(
                            [html.Label("Состояние"), dcc.Dropdown(id="state-filter", multi=True, placeholder="Все")],
                            md=2,
                            xs=12,
                        ),
                        dbc.Col(
                            [
                                html.Label("Уволенные"),
                                dcc.Dropdown(
                                    id="dismissed-filter",
                                    options=[
                                        {"label": "Все", "value": "all"},
                                        {"label": "Только активные", "value": "active"},
                                        {"label": "Только уволенные", "value": "dismissed"},
                                    ],
                                    value="all",
                                    clearable=False,
                                ),
                            ],
                            md=2,
                            xs=12,
                        ),
                        dbc.Col(
                            [html.Label("Год приёма"), dcc.Dropdown(id="hire-year-filter", multi=True, placeholder="Все годы")],
                            md=2,
                            xs=12,
                        ),
                    ],
                    className="g-3 mb-3",
                ),
                dcc.Input(
                    id="search-input",
                    type="text",
                    placeholder="Введите ФИО сотрудника...",
                    debounce=True,
                    className="form-control",
                ),
                html.Div(id="employee-search-panel", className="mt-3"),
            ]
        ),
        className="mb-4 shadow-sm",
    )


def _table(id_suffix: str, page_size: int = 15) -> dash_table.DataTable:
    style_data_conditional = []
    if id_suffix == "overview-employees":
        style_data_conditional = [
            {
                "if": {"filter_query": '{state} = "Уволенные"'},
                "backgroundColor": "#f8d7da",
                "color": "#58151c",
            }
        ]
    return dash_table.DataTable(
        id=f"{id_suffix}-table",
        page_size=page_size,
        sort_action="native",
        filter_action="native" if id_suffix == "overview-employees" else "none",
        style_table={"overflowX": "auto"},
        style_cell={"textAlign": "left", "padding": "8px", "fontSize": "14px", "whiteSpace": "normal"},
        style_header={"fontWeight": "bold", "backgroundColor": "#f8f9fa"},
        style_data_conditional=style_data_conditional,
    )


def _employee_profile_card(profile: dict) -> dbc.Card:
    harmful_color = "danger" if profile["harmful"] == "Да" else "success"
    is_dismissed = profile["state"] == "Уволенные"
    state_color = "secondary" if is_dismissed else "light"
    state_text_color = "white" if is_dismissed else "dark"
    return dbc.Card(
        dbc.CardBody(
            [
                html.H5(profile["full_name"], className="mb-1"),
                html.Div(
                    f"Таб. № {profile['source_id']} · {profile['position']} · {profile['department']}",
                    className="text-muted small mb-3",
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.Div("Дата приёма", className="text-muted small"),
                                html.Strong(profile["hire_date"]),
                            ],
                            md=4,
                            xs=12,
                        ),
                        dbc.Col(
                            [
                                html.Div("Стаж", className="text-muted small"),
                                html.Strong(profile["tenure"]),
                            ],
                            md=4,
                            xs=12,
                        ),
                        dbc.Col(
                            [
                                html.Div("Вредник", className="text-muted small"),
                                dbc.Badge(profile["harmful"], color=harmful_color, className="fs-6"),
                            ],
                            md=4,
                            xs=12,
                        ),
                    ],
                    className="g-2",
                ),
                html.Div(
                    [
                        html.Span("Состояние: ", className="text-muted small"),
                        dbc.Badge(profile["state"], color=state_color, text_color=state_text_color),
                    ],
                    className="mt-3 mb-0",
                ),
            ]
        ),
        className="shadow-sm mb-3",
    )


def _build_employee_search_panel(df: pd.DataFrame, search_value: str | None):
    matches = find_employees_by_query(df, search_value)
    if matches.empty:
        if search_value and str(search_value).strip():
            return dbc.Alert("Сотрудник не найден", color="warning", className="mb-0")
        return html.Div()

    cards = [_employee_profile_card(employee_profile(row)) for _, row in matches.iterrows()]
    total = len(find_employees_by_query(df, search_value, limit=1000))
    title = html.Div(
        f"Найдено сотрудников: {total}" + (f" (показаны первые {len(cards)})" if total > len(cards) else ""),
        className="text-muted small mb-2",
    )
    return html.Div([title, *cards])


def _serialize_last_run(last_run):
    if not last_run:
        return None
    return {
        "status": last_run.status,
        "rows_loaded": last_run.rows_loaded,
        "rows_rejected": last_run.rows_rejected,
        "finished_at": str(last_run.finished_at),
    }


def create_app() -> dash.Dash:
    app = dash.Dash(
        __name__,
        external_stylesheets=[dbc.themes.FLATLY],
        title="HR Dashboard",
        suppress_callback_exceptions=True,
    )

    app.layout = dbc.Container(
        [
            html.H1("HR Dashboard", className="mt-4 mb-2"),
            html.P("Аналитика кадровых данных: персонал, структура, охрана труда, качество данных", className="text-muted"),
            dbc.Button("Обновить данные", id="refresh-btn", color="primary", className="mb-3"),
            _filters_card(),
            dcc.Tabs(
                id="tabs",
                value="overview",
                children=[
                    dcc.Tab(
                        label="Обзор",
                        value="overview",
                        children=[
                            html.Div(id="overview-kpis"),
                            dbc.Row(
                                [
                                    dbc.Col(dcc.Graph(id="overview-dept-chart"), md=6, xs=12),
                                    dbc.Col(dcc.Graph(id="overview-gender-chart"), md=6, xs=12),
                                ],
                                className="g-3 mb-4",
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(dcc.Graph(id="overview-hire-chart"), md=6, xs=12),
                                    dbc.Col(dcc.Graph(id="overview-state-chart"), md=6, xs=12),
                                ],
                                className="g-3 mb-4",
                            ),
                            html.H4("Сотрудники"),
                            _table("overview-employees"),
                        ],
                        className="pt-3",
                    ),
                    dcc.Tab(
                        label="Структура",
                        value="structure",
                        children=[
                            html.Div(id="structure-kpis"),
                            dbc.Row(
                                [
                                    dbc.Col(dcc.Graph(id="structure-dept-chart"), md=6, xs=12),
                                    dbc.Col(dcc.Graph(id="structure-position-chart"), md=6, xs=12),
                                ],
                                className="g-3 mb-4",
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(dcc.Graph(id="structure-heatmap-chart"), md=6, xs=12),
                                    dbc.Col(dcc.Graph(id="structure-tenure-chart"), md=6, xs=12),
                                ],
                                className="g-3 mb-4",
                            ),
                        ],
                        className="pt-3",
                    ),
                    dcc.Tab(
                        label="Охрана труда",
                        value="safety",
                        children=[
                            html.Div(id="safety-kpis"),
                            dbc.Row(
                                [
                                    dbc.Col(dcc.Graph(id="safety-harmful-chart"), md=6, xs=12),
                                    dbc.Col(dcc.Graph(id="safety-permits-chart"), md=6, xs=12),
                                ],
                                className="g-3 mb-4",
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(dcc.Graph(id="safety-cert-chart"), md=6, xs=12),
                                    dbc.Col(dcc.Graph(id="safety-overdue-chart"), md=6, xs=12),
                                ],
                                className="g-3 mb-4",
                            ),
                            html.H4("Сотрудники с рисками"),
                            _table("safety-risk", page_size=10),
                        ],
                        className="pt-3",
                    ),
                    dcc.Tab(
                        label="Статистические критерии",
                        value="statistics",
                        children=[
                            html.H4("Формальная проверка гипотез", className="mt-3"),
                            html.P(
                                "Расчёты выполняются на текущей выборке после применения фильтров. "
                                "Уровень значимости α = 0,05; p-value сравнивается с α.",
                                className="text-muted",
                            ),
                            html.Div(id="hypothesis-tests-content"),
                            html.Div(
                                "Интерпретация: если p-value < α, нулевая гипотеза отвергается; иначе статистически значимых оснований для её отклонения нет.",
                                className="text-muted small mt-3 mb-3",
                            ),
                        ],
                        className="pt-3",
                    ),
                    dcc.Tab(
                        label="Качество данных",
                        value="quality",
                        children=[
                            html.Div(id="quality-kpis"),
                            dbc.Row(
                                [
                                    dbc.Col(dcc.Graph(id="quality-fill-chart"), md=6, xs=12),
                                    dbc.Col(dcc.Graph(id="quality-reject-chart"), md=6, xs=12),
                                ],
                                className="g-3 mb-4",
                            ),
                            html.H4("Заполненность полей"),
                            _table("quality-fields", page_size=20),
                            html.H4("Последние запуски ETL", className="mt-4"),
                            _table("quality-runs", page_size=10),
                        ],
                        className="pt-3",
                    ),
                ],
            ),
            dcc.Store(id="employees-store"),
            dcc.Store(id="filtered-store"),
            dcc.Store(id="meta-store"),
        ],
        fluid=True,
    )

    @app.callback(
        Output("employees-store", "data"),
        Output("department-filter", "options"),
        Output("gender-filter", "options"),
        Output("state-filter", "options"),
        Output("hire-year-filter", "options"),
        Output("meta-store", "data"),
        Input("refresh-btn", "n_clicks"),
        prevent_initial_call=False,
    )
    def refresh_data(_n_clicks):
        employees = prepare_employees(load_employees())
        options = build_filter_options(employees)
        meta = {
            "rejects": int(load_reject_summary()["reject_count"].sum()) if not load_reject_summary().empty else 0,
            "last_run": _serialize_last_run(load_last_run()),
            "runs": load_etl_runs().astype(str).to_dict("records"),
            "rejects_summary": load_reject_summary().to_dict("records"),
        }
        return (
            employees.to_dict("records"),
            options["departments"],
            options["genders"],
            options["states"],
            options["years"],
            meta,
        )

    @app.callback(
        Output("employee-search-panel", "children"),
        Input("employees-store", "data"),
        Input("search-input", "value"),
        prevent_initial_call=False,
    )
    def update_employee_search_panel(store_data, search_value):
        if not store_data:
            return html.Div()
        df = prepare_employees(pd.DataFrame(store_data))
        return _build_employee_search_panel(df, search_value)

    @app.callback(
        Output("filtered-store", "data"),
        Input("employees-store", "data"),
        Input("department-filter", "value"),
        Input("gender-filter", "value"),
        Input("harmful-filter", "value"),
        Input("state-filter", "value"),
        Input("dismissed-filter", "value"),
        Input("hire-year-filter", "value"),
        Input("search-input", "value"),
        prevent_initial_call=False,
    )
    def update_filtered_store(
        store_data, departments, genders, harmful_filter, states, dismissed_filter, hire_years, search_value
    ):
        if not store_data:
            return []
        df = prepare_employees(pd.DataFrame(store_data))
        filtered = apply_filters(
            df, departments, genders, harmful_filter, states, hire_years, search_value, dismissed_filter
        )
        return filtered.to_dict("records")

    @app.callback(
        Output("overview-kpis", "children"),
        Output("overview-dept-chart", "figure"),
        Output("overview-gender-chart", "figure"),
        Output("overview-hire-chart", "figure"),
        Output("overview-state-chart", "figure"),
        Output("overview-employees-table", "data"),
        Output("overview-employees-table", "columns"),
        Input("filtered-store", "data"),
        prevent_initial_call=False,
    )
    def update_overview_tab(filtered_data):
        if not filtered_data:
            empty = charts.empty_figure()
            return html.Div(), empty, empty, empty, empty, [], []

        df = prepare_employees(pd.DataFrame(filtered_data))
        kpis = overview_kpis(df)
        kpi_row = _kpi_row(
            [
                ("Численность", kpis["employees"], "сотрудников"),
                ("М / Ж", kpis["male_female"], "распределение по полу"),
                ("Средний стаж", kpis["avg_tenure"], "по hire_date"),
                ("Новые за год", kpis["new_year"], str(date.today().year)),
                ("На вредных", f"{kpis['harmful']} ({kpis['harmful_pct']})", "harmful = true"),
                ("В отпуске", kpis["on_leave"], "отпуск / приостановка"),
                ("Уволенные", kpis["dismissed"], "нет в Excel"),
            ]
        )
        table_df = df[
            [
                "source_id",
                "full_name",
                "department",
                "position",
                "gender",
                "hire_date",
                "tenure_years",
                "state_norm",
                "harmful",
            ]
        ].copy()
        table_df["hire_date"] = table_df["hire_date"].apply(format_hire_date)
        table_df["tenure"] = table_df["tenure_years"].apply(format_tenure)
        table_df["state"] = table_df["state_norm"]
        table_df = table_df.drop(columns=["tenure_years", "state_norm"])
        records, columns = table_records(table_df)
        return (
            kpi_row,
            charts.department_bar(df),
            charts.gender_pie(df),
            charts.hire_line(df),
            charts.state_bar(df),
            records,
            columns,
        )

    @app.callback(
        Output("structure-kpis", "children"),
        Output("structure-dept-chart", "figure"),
        Output("structure-position-chart", "figure"),
        Output("structure-heatmap-chart", "figure"),
        Output("structure-tenure-chart", "figure"),
        Input("filtered-store", "data"),
        prevent_initial_call=False,
    )
    def update_structure_tab(filtered_data):
        if not filtered_data:
            empty = charts.empty_figure()
            return html.Div(), empty, empty, empty, empty

        df = prepare_employees(pd.DataFrame(filtered_data))
        kpis = structure_kpis(df)
        kpi_row = _kpi_row(
            [
                ("Отделов", kpis["departments"], "уникальных"),
                ("Должностей", kpis["positions"], "уникальных"),
                ("Самый большой отдел", kpis["largest_dept"], ""),
                ("Самый маленький отдел", kpis["smallest_dept"], ""),
            ]
        )
        return (
            kpi_row,
            charts.department_bar(df, title="Top-15 отделов"),
            charts.position_bar(df),
            charts.department_gender_heatmap(df),
            charts.tenure_by_department(df),
        )

    @app.callback(
        Output("safety-kpis", "children"),
        Output("safety-harmful-chart", "figure"),
        Output("safety-permits-chart", "figure"),
        Output("safety-cert-chart", "figure"),
        Output("safety-overdue-chart", "figure"),
        Output("safety-risk-table", "data"),
        Output("safety-risk-table", "columns"),
        Input("filtered-store", "data"),
        prevent_initial_call=False,
    )
    def update_safety_tab(filtered_data):
        if not filtered_data:
            empty = charts.empty_figure()
            return html.Div(), empty, empty, empty, empty, [], []

        df = prepare_employees(pd.DataFrame(filtered_data))
        kpis = safety_kpis(df)
        kpi_row = _kpi_row(
            [
                ("Вредники", kpis["harmful"], "harmful = true"),
                ("Работы на высоте", kpis["height"], "заполнено height"),
                ("Люльки", kpis["cradle"], "заполнено cradle"),
                ("Пожарная безоп.", kpis["fire_filled"], "заполнено fire_safety"),
                ("Просрочки", kpis["overdue"], "по всем аттестациям"),
            ]
        )
        risk_df = risk_table(df)
        records, columns = table_records(risk_df)
        return (
            kpi_row,
            charts.harmful_by_department(df),
            charts.permits_by_type(df),
            charts.cert_status_chart(df),
            charts.overdue_heatmap(df),
            records,
            columns,
        )

    @app.callback(
        Output("hypothesis-tests-content", "children"),
        Input("filtered-store", "data"),
        prevent_initial_call=False,
    )
    def update_statistics_tab(filtered_data):
        if not filtered_data:
            return html.Div()
        df = prepare_employees(pd.DataFrame(filtered_data))
        results = hypothesis_tests(df)
        return [_hypothesis_card(result, number) for number, result in enumerate(results, start=1)]

    @app.callback(
        Output("quality-kpis", "children"),
        Output("quality-fill-chart", "figure"),
        Output("quality-reject-chart", "figure"),
        Output("quality-fields-table", "data"),
        Output("quality-fields-table", "columns"),
        Output("quality-runs-table", "data"),
        Output("quality-runs-table", "columns"),
        Input("filtered-store", "data"),
        Input("meta-store", "data"),
        prevent_initial_call=False,
    )
    def update_quality_tab(filtered_data, meta):
        empty = charts.empty_figure()
        if not filtered_data or not meta:
            return html.Div(), empty, empty, [], [], [], []

        df = prepare_employees(pd.DataFrame(filtered_data))
        last_run = meta.get("last_run")
        kpis = quality_kpis(df, meta.get("rejects", 0), last_run)
        fill_rates = field_fill_rates(df)
        kpi_row = _kpi_row(
            [
                ("Data Quality Score", kpis["quality_score"], "средняя заполненность"),
                ("Без пола", kpis["missing_gender"], "gender is null"),
                ("Без отдела", kpis["missing_department"], "department is null"),
                ("Reject-записи", kpis["rejects"], "staging.hr_rejects"),
                ("Последний ETL", kpis["last_etl"], "audit.hr_etl_runs"),
            ]
        )
        rejects_df = pd.DataFrame(meta.get("rejects_summary", []))
        runs_df = pd.DataFrame(meta.get("runs", []))
        return (
            kpi_row,
            charts.fill_rate_chart(fill_rates),
            charts.rejects_chart(rejects_df),
            fill_rates,
            [{"name": "field", "id": "field"}, {"name": "filled", "id": "filled"}, {"name": "fill_pct", "id": "fill_pct"}],
            runs_df.to_dict("records"),
            [{"name": col, "id": col} for col in runs_df.columns],
        )

    return app


app = create_app()


def main():
    app.run(host=DASH_HOST, port=DASH_PORT, debug=DASH_DEBUG)


if __name__ == "__main__":
    main()
