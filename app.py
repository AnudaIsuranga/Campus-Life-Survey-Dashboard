from __future__ import annotations

import json
import re
from datetime import datetime

import pandas as pd
from dash import Dash, Input, Output, State, ALL, ctx, dcc, html, dash_table, no_update
from dash.exceptions import PreventUpdate

from utils.analysis import (
    DRILLDOWN_FACTORS,
    apply_filters,
    feedback_records,
    improvement_counts,
    kpis,
    mobile_frequency_counts,
    mobile_reason_counts,
    programme_heatmap,
    programme_overall_means,
    score_distribution,
    satisfaction_means,
    spearman_for_factor,
    visit_overall_means,
    response_table,
)
from utils.charts import (
    heatmap_chart,
    issue_chart,
    means_chart,
    mobile_reason_chart,
    overall_distribution_chart,
    programme_chart,
    scatter_chart,
    visit_chart,
)
from utils.data_processing import (
    FRIENDLY_NAMES,
    dataframe_from_json,
    dataframe_to_json,
    load_uploaded_contents,
)


APP_TITLE = "Campus Life & Student Satisfaction Analytics"

NAV_ITEMS = [
    ("/overview", "Overview", "⌂"),
    ("/satisfaction", "Satisfaction", "▥"),
    ("/issues", "Campus Issues", "△"),
    ("/drilldown", "Drill-down Analysis", "◎"),
    ("/responses", "Response Explorer", "▤"),
    ("/feedback", "Feedback", "▢"),
]

FILTER_DEFAULTS = {
    "age": "__all__",
    "gender": "__all__",
    "programme": "__all__",
    "visit": "__all__",
}

app = Dash(
    __name__,
    suppress_callback_exceptions=True,
    title=APP_TITLE,
)

server = app.server


# ============================================================
# BASIC UI HELPERS
# ============================================================

def icon(symbol: str, active: bool = False) -> html.Span:
    return html.Span(
        symbol,
        className="nav-icon" + (" active" if active else ""),
    )


def logo_block(compact: bool = False) -> html.Div:
    return html.Div(
        [
            html.Div("◆", className="brand-mark"),
            html.Div(
                [
                    html.Div("Contra campus", className="brand-name"),
                    html.Div("ANALYTICS CONSOLE", className="brand-sub"),
                ],
                className="brand-copy",
            ),
        ],
        className="brand",
    )


def sidebar() -> html.Aside:
    nav = html.Nav(
        [
            dcc.Link(
                [
                    icon(symbol),
                    html.Span(label),
                ],
                href=href,
                className="nav-link",
                id=f"nav-{label.lower().replace(' ', '-').replace('/', '-')}",
            )
            for href, label, symbol in NAV_ITEMS
        ],
        className="sidebar-nav",
    )

    return html.Aside(
        [
            html.Div(
                logo_block(),
                className="sidebar-brand-wrap",
            ),

            nav,

            html.Div(style={"flex": 1}),

            html.Div(
                [
                    html.Div(
                        [
                            html.Span("DATASET STATUS"),
                            html.Span(
                                "•",
                                id="dataset-dot",
                                className="status-dot",
                            ),
                        ],
                        className="status-card-head",
                    ),

                    html.Div(
                        "No Active Data",
                        id="sidebar-dataset-status",
                        className="status-card-value",
                    ),

                    html.Div(
                        "Please upload survey feedback",
                        id="sidebar-dataset-meta",
                        className="status-card-meta",
                    ),
                ],
                className="sidebar-status-card",
            ),

            html.Button(
                ["⇧  Upload Dataset"],
                id="sidebar-upload-btn",
                className="sidebar-upload-btn",
            ),
        ],
        className="sidebar",
    )


def mobile_header() -> html.Div:
    return html.Div(
        [
            logo_block(),

            dcc.Dropdown(
                id="mobile-nav",
                options=[
                    {
                        "label": label,
                        "value": href,
                    }
                    for href, label, _ in NAV_ITEMS
                ],
                value="/overview",
                clearable=False,
                searchable=False,
                className="mobile-nav-dropdown",
            ),
        ],
        className="mobile-header",
    )


def header() -> html.Header:
    return html.Header(
        [
            html.Div(
                [
                    html.H1(
                        APP_TITLE,
                        id="page-title",
                        className="page-title",
                    ),

                    html.Div(
                        "Dashboard ready for Google Forms CSV/XLSX batch ingestion",
                        id="page-subtitle",
                        className="page-subtitle",
                    ),
                ],
                className="title-wrap",
            ),

            html.Div(
                [
                    html.Div(
                        [
                            html.Span(
                                "•",
                                className="live-dot",
                            ),
                            html.Span(
                                "Static Dashboard",
                                id="dataset-badge-text",
                            ),
                        ],
                        id="dataset-badge",
                        className="dataset-badge",
                    ),

                    html.Button(
                        ["↻  Refresh Data"],
                        id="refresh-btn",
                        className="secondary-btn",
                    ),

                    html.Button(
                        ["⇧  Upload CSV/XLSX"],
                        id="header-upload-btn",
                        className="primary-btn",
                    ),
                ],
                className="header-actions",
            ),
        ],
        className="page-header",
    )


def filter_bar() -> html.Div:

    def dropdown_block(
        label: str,
        component_id: str,
        placeholder: str,
    ) -> html.Div:

        return html.Div(
            [
                html.Div(
                    label,
                    className="filter-label",
                ),

                dcc.Dropdown(
                    id=component_id,
                    options=[],
                    value="__all__",
                    clearable=False,
                    searchable=False,
                    placeholder=placeholder,
                    className="filter-dropdown",
                ),
            ],
            className="filter-field",
        )

    return html.Div(
        [
            html.Div(
                [
                    html.Span(
                        "⌁",
                        className="filter-symbol",
                    ),
                    html.Span(
                        "Filters",
                        className="filter-title",
                    ),
                ],
                className="filter-title-wrap",
            ),

            dropdown_block(
                "Age Group",
                "filter-age",
                "All Ages",
            ),

            dropdown_block(
                "Gender",
                "filter-gender",
                "All Genders",
            ),

            dropdown_block(
                "Programme",
                "filter-programme",
                "All Programmes",
            ),

            dropdown_block(
                "Visit Frequency",
                "filter-visit",
                "All Frequencies",
            ),

            html.Div(style={"flex": 1}),

            html.Button(
                "Reset",
                id="reset-filters",
                className="link-btn",
            ),

            html.Button(
                "Apply Filters",
                id="apply-filters",
                className="apply-btn",
            ),
        ],
        id="filters-container",
        className="filter-bar",
    )


def status_line() -> html.Div:
    return html.Div(
        id="filter-status",
        className="status-line",
    )


def card(
    children,
    class_name: str = "panel-card",
) -> html.Div:
    return html.Div(
        children,
        className=class_name,
    )


def kpi_card(
    title: str,
    value: str,
    subtext: str,
    tone: str = "cyan",
) -> html.Div:

    return html.Div(
        [
            html.Div(
                title,
                className="kpi-label",
            ),

            html.Div(
                value,
                className=f"kpi-value {tone}",
            ),

            html.Div(
                subtext,
                className="kpi-subtext",
            ),
        ],
        className="kpi-card",
    )


# ============================================================
# EMPTY / PLACEHOLDER STATE
# ============================================================

def placeholder_overview() -> html.Div:

    return html.Div(
        [
            card(
                [
                    html.Div(
                        "⌁",
                        className="empty-icon",
                    ),

                    html.H2(
                        "No active survey dataset loaded",
                        className="empty-title",
                    ),

                    html.P(
                        "Upload your Google Forms CSV or XLSX file to begin analysis. "
                        "The console maps survey variables, recalculates statistical "
                        "summaries, and refreshes every interactive view automatically.",
                        className="empty-copy",
                    ),

                    html.Button(
                        [
                            "▣  Browse Files & Ingest Dataset"
                        ],
                        id="empty-upload-btn",
                        className="primary-btn empty-upload-btn",
                    ),
                ],
                "empty-panel",
            ),

            html.Div(
                [
                    kpi_card(
                        "TOTAL RESPONSES",
                        "--",
                        "No active data metrics",
                        "muted",
                    ),

                    kpi_card(
                        "MEAN CAMPUS SATISFACTION",
                        "--",
                        "No active data metrics",
                        "muted",
                    ),

                    kpi_card(
                        "LOW SATISFACTION RATE",
                        "--",
                        "No active data metrics",
                        "muted",
                    ),

                    kpi_card(
                        "CRITICAL SERVICE AREA",
                        "--",
                        "No active data metrics",
                        "muted",
                    ),
                ],
                className="kpi-grid muted-grid",
            ),

            html.Div(
                [
                    card(
                        [
                            html.H3(
                                "Overall Experience Distribution (Awaiting Dataset)",
                                className="panel-title",
                            ),

                            html.Div(
                                className="skeleton-list"
                            ),
                        ]
                    ),

                    card(
                        [
                            html.H3(
                                "Programme × Mean Campus Satisfaction (Awaiting Dataset)",
                                className="panel-title",
                            ),

                            html.Div(
                                className="skeleton-grid"
                            ),
                        ]
                    ),
                ],
                className="content-grid two-col",
            ),
        ]
    )


def data_missing_page(
    section: str,
) -> html.Div:

    return card(
        [
            html.Div(
                "⌁",
                className="empty-icon small",
            ),

            html.H2(
                f"No active dataset for {section}",
                className="empty-title",
            ),

            html.P(
                "Upload the Google Forms CSV/XLSX dataset to activate this view. "
                "All metrics are intentionally blank until a dataset is loaded.",
                className="empty-copy",
            ),
        ],
        "empty-panel page-empty",
    )


# ============================================================
# KPI / OVERVIEW COMPONENTS
# ============================================================

def loaded_kpis(
    df: pd.DataFrame,
) -> html.Div:

    stats = kpis(df)

    mean = (
        f"{stats['mean']:.2f}/5"
        if stats["mean"] is not None
        else "—"
    )

    low = (
        f"{stats['low_rate']:.1f}%"
        if stats["low_rate"] is not None
        else "—"
    )

    critical = (
        stats["critical"]
        if stats["critical"]
        else "—"
    )

    valid_score_pct = (
        f"{(stats['mean_n'] / stats['responses'] * 100):.0f}% "
        f"of rows have a valid overall score"
        if stats["responses"]
        else "No rows"
    )

    critical_subtext = (
        f"{stats['critical_count']} respondents selected it in multi-select"
        if stats["critical_count"]
        else "No improvement selections"
    )

    return html.Div(
        [
            kpi_card(
                "TOTAL SURVEY RESPONSES",
                f"{stats['responses']:,}",
                valid_score_pct,
                "cyan",
            ),

            kpi_card(
                "MEAN CAMPUS SATISFACTION",
                mean,
                "Overall campus experience · 1–5 Likert",
                "blue",
            ),

            kpi_card(
                "LOW SATISFACTION RATE",
                low,
                "Overall score < 3.0",
                "red",
            ),

            kpi_card(
                "CRITICAL SERVICE AREA",
                critical,
                critical_subtext,
                "orange",
            ),
        ],
        className="kpi-grid",
    )


def progress_list(
    df: pd.DataFrame,
    top_n: int = 5,
) -> html.Div:

    counts = improvement_counts(df).head(top_n)

    if counts.empty:
        return html.Div(
            "No improvement-area selections available.",
            className="empty-inline",
        )

    max_count = float(
        counts["responses"].max()
    )

    children = []

    for i, row in counts.iterrows():

        width = (
            float(row["responses"])
            / max_count
            * 100
            if max_count
            else 0
        )

        tone_class = (
            "bar-cyan"
            if i == 0
            else "bar-blue"
        )

        children.append(
            html.Div(
                [
                    html.Div(
                        [
                            html.Span(
                                str(row["area"]),
                                className="metric-name",
                            ),

                            html.Span(
                                f"{int(row['responses'])} votes "
                                f"({row['pct']:.1f}%)",
                                className="metric-value",
                            ),
                        ],
                        className="metric-head",
                    ),

                    html.Div(
                        html.Div(
                            style={
                                "width": f"{width:.1f}%"
                            },
                            className=(
                                f"metric-fill {tone_class}"
                            ),
                        ),
                        className="metric-track",
                    ),
                ],
                className="metric-row",
            )
        )

    return html.Div(
        children,
        className="metric-list",
    )


# ============================================================
# FIXED MOBILE DATA PANEL
# ============================================================

def mobile_panel(
    df: pd.DataFrame,
) -> html.Div:

    counts = mobile_frequency_counts(df)

    n = (
        int(counts["responses"].sum())
        if not counts.empty
        else 0
    )

    if not n:
        return html.Div(
            "No mobile-data responses available.",
            className="empty-inline",
        )

    groups = [
        (
            "Always",
            "Heavily reliant on personal mobile data",
            "Campus Wi-Fi is frequently supplemented by mobile data",
            "red",
        ),
        (
            "Often / Sometimes",
            "Regular mobile-data fallback while on campus",
            "Students use mobile data when campus connectivity is insufficient",
            "orange",
        ),
        (
            "Rarely / Never",
            "Limited personal mobile-data use",
            "Mostly rely on campus connectivity",
            "green",
        ),
    ]

    values = {
        "Always": int(
            counts.loc[
                counts["frequency"] == "Always",
                "responses",
            ].sum()
        ),

        "Often / Sometimes": int(
            counts.loc[
                counts["frequency"].isin(
                    [
                        "Often",
                        "Sometimes",
                    ]
                ),
                "responses",
            ].sum()
        ),

        "Rarely / Never": int(
            counts.loc[
                counts["frequency"].isin(
                    [
                        "Rarely",
                        "Never",
                    ]
                ),
                "responses",
            ].sum()
        ),
    }

    rows = []

    for key, title, sub, tone in groups:

        pct = (
            values[key] / n * 100
            if n
            else 0
        )

        rows.append(
            html.Div(
                [
                    html.Div(
                        [
                            html.Span(
                                "",
                                className=(
                                    f"status-strip {tone}"
                                ),
                            ),

                            html.Div(
                                [
                                    html.Div(
                                        title,
                                        className="mobile-title",
                                    ),

                                    html.Div(
                                        sub,
                                        className="mobile-sub",
                                    ),
                                ]
                            ),
                        ],
                        className="mobile-left",
                    ),

                    html.Div(
                        f"{pct:.1f}%",
                        className=(
                            f"mobile-pct {tone}"
                        ),
                    ),
                ],
                className="mobile-row",
            )
        )

    return html.Div(
        rows,
        className="mobile-list",
    )


def feedback_panel(
    df: pd.DataFrame,
    limit: int = 3,
) -> html.Div:

    records = feedback_records(
        df,
        limit=limit,
    )

    if not records:
        return html.Div(
            "No written feedback is available in the current filtered view.",
            className="empty-inline",
        )

    return html.Div(
        [
            html.Div(
                [
                    html.P(
                        r["text"],
                        className="feedback-text",
                    ),

                    html.Div(
                        f"{r['programme']} · Visit: {r['visit']}",
                        className="feedback-meta",
                    ),
                ],
                className="feedback-item",
            )
            for r in records
        ],
        className="feedback-list",
    )


# ============================================================
# PAGES
# ============================================================

def overview_page(
    df: pd.DataFrame,
) -> html.Div:

    if df.empty:
        return placeholder_overview()

    heat = programme_heatmap(df)

    improvement = improvement_counts(df)

    total_selections = (
        int(improvement["responses"].sum())
        if not improvement.empty
        else 0
    )

    return html.Div(
        [
            loaded_kpis(df),

            html.Div(
                [
                    card(
                        [
                            html.Div(
                                [
                                    html.H3(
                                        "Overall Experience Distribution",
                                        className="panel-title",
                                    ),

                                    html.Span(
                                        f"n={len(df):,}",
                                        className="panel-meta",
                                    ),
                                ],
                                className="panel-head",
                            ),

                            dcc.Graph(
                                figure=overall_distribution_chart(
                                    score_distribution(df)
                                ),
                                config={
                                    "displayModeBar": False
                                },
                                className="plotly-graph",
                            ),
                        ],
                        "panel-card chart-card",
                    ),

                    card(
                        [
                            html.Div(
                                [
                                    html.H3(
                                        "Programme × Mean Campus Satisfaction",
                                        className="panel-title",
                                    ),

                                    html.Span(
                                        "Five focus measures",
                                        className="panel-meta",
                                    ),
                                ],
                                className="panel-head",
                            ),

                            dcc.Graph(
                                figure=heatmap_chart(
                                    heat
                                ),
                                config={
                                    "displayModeBar": False
                                },
                                className="plotly-graph",
                            ),
                        ],
                        "panel-card chart-card",
                    ),
                ],
                className="content-grid two-col",
            ),

            card(
                [
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.H3(
                                        "What Needs Improvement?",
                                        className="panel-title",
                                    ),

                                    html.Div(
                                        "Respondents could select multiple areas",
                                        className="panel-subtitle",
                                    ),
                                ]
                            ),

                            html.Div(
                                f"{total_selections} total selections",
                                className="selection-badge",
                            ),
                        ],
                        className="panel-head",
                    ),

                    progress_list(df),
                ],
                "panel-card",
            ),

            html.Div(
                [
                    card(
                        [
                            html.H3(
                                "Campus Wi-Fi & Mobile Data Usage",
                                className="panel-title",
                            ),

                            mobile_panel(df),
                        ],
                        "panel-card",
                    ),

                    card(
                        [
                            html.H3(
                                "Anonymous Student Feedback (Latest Entries)",
                                className="panel-title",
                            ),

                            feedback_panel(
                                df,
                                3,
                            ),
                        ],
                        "panel-card",
                    ),
                ],
                className="content-grid two-col",
            ),
        ]
    )


def satisfaction_page(
    df: pd.DataFrame,
) -> html.Div:

    if df.empty:
        return data_missing_page(
            "Satisfaction Analytics"
        )

    means = satisfaction_means(df)

    return html.Div(
        [
            html.Div(
                [
                    card(
                        [
                            html.Div(
                                [
                                    html.H3(
                                        "Mean Satisfaction by Survey Factor",
                                        className="panel-title",
                                    ),

                                    html.Span(
                                        "All 13 Likert measures",
                                        className="panel-meta",
                                    ),
                                ],
                                className="panel-head",
                            ),

                            dcc.Graph(
                                figure=means_chart(
                                    means
                                ),
                                config={
                                    "displayModeBar": False
                                },
                            ),
                        ],
                        "panel-card chart-card",
                    ),

                    card(
                        [
                            html.Div(
                                [
                                    html.H3(
                                        "Overall Experience by Programme",
                                        className="panel-title",
                                    ),

                                    html.Span(
                                        "Filtered current view",
                                        className="panel-meta",
                                    ),
                                ],
                                className="panel-head",
                            ),

                            dcc.Graph(
                                figure=programme_chart(
                                    programme_overall_means(df)
                                ),
                                config={
                                    "displayModeBar": False
                                },
                            ),
                        ],
                        "panel-card chart-card",
                    ),
                ],
                className="content-grid two-col",
            ),

            html.Div(
                [
                    card(
                        [
                            html.Div(
                                [
                                    html.H3(
                                        "Overall Experience by Visit Frequency",
                                        className="panel-title",
                                    ),

                                    html.Span(
                                        "Mean overall score",
                                        className="panel-meta",
                                    ),
                                ],
                                className="panel-head",
                            ),

                            dcc.Graph(
                                figure=visit_chart(
                                    visit_overall_means(df)
                                ),
                                config={
                                    "displayModeBar": False
                                },
                            ),
                        ],
                        "panel-card chart-card",
                    ),

                    card(
                        [
                            html.H3(
                                "Interpretation Guide",
                                className="panel-title",
                            ),

                            html.Div(
                                [
                                    html.Div(
                                        "1–2",
                                        className="guide-score red",
                                    ),

                                    html.Div(
                                        "Dissatisfied / poor",
                                        className="guide-label",
                                    ),

                                    html.Div(
                                        "3",
                                        className="guide-score cyan",
                                    ),

                                    html.Div(
                                        "Neutral / moderate",
                                        className="guide-label",
                                    ),

                                    html.Div(
                                        "4–5",
                                        className="guide-score green",
                                    ),

                                    html.Div(
                                        "Satisfied / very satisfied",
                                        className="guide-label",
                                    ),
                                ],
                                className="guide-grid",
                            ),
                        ],
                        "panel-card guide-card",
                    ),
                ],
                className="content-grid two-col",
            ),
        ]
    )


def issues_page(
    df: pd.DataFrame,
) -> html.Div:

    if df.empty:
        return data_missing_page(
            "Campus Issues"
        )

    issues = improvement_counts(df)

    reasons = mobile_reason_counts(df)

    return html.Div(
        [
            html.Div(
                [
                    card(
                        [
                            html.Div(
                                [
                                    html.H3(
                                        "Priority Areas for Improvement",
                                        className="panel-title",
                                    ),

                                    html.Span(
                                        "Multi-select respondent mentions",
                                        className="panel-meta",
                                    ),
                                ],
                                className="panel-head",
                            ),

                            dcc.Graph(
                                figure=issue_chart(
                                    issues
                                ),
                                config={
                                    "displayModeBar": False
                                },
                            ),
                        ],
                        "panel-card chart-card",
                    ),

                    card(
                        [
                            html.Div(
                                [
                                    html.H3(
                                        "Reasons for Using Personal Mobile Data / Hotspot",
                                        className="panel-title",
                                    ),

                                    html.Span(
                                        "Multi-select respondent mentions",
                                        className="panel-meta",
                                    ),
                                ],
                                className="panel-head",
                            ),

                            dcc.Graph(
                                figure=mobile_reason_chart(
                                    reasons
                                ),
                                config={
                                    "displayModeBar": False
                                },
                            ),
                        ],
                        "panel-card chart-card",
                    ),
                ],
                className="content-grid two-col",
            ),

            card(
                [
                    html.H3(
                        "Issue Context",
                        className="panel-title",
                    ),

                    html.P(
                        "The dashboard counts each selected improvement or "
                        "mobile-data reason once per respondent, so multi-select "
                        "questions can exceed the total respondent count. This "
                        "preserves the survey design while making the frequency "
                        "interpretation explicit.",
                        className="panel-copy",
                    ),
                ],
                "panel-card",
            ),
        ]
    )


# ============================================================
# DRILL DOWN
# ============================================================

def factor_tabs(
    active_factor: str,
) -> html.Div:

    return html.Div(
        [
            html.Div(
                "Selected Factor:",
                className="tabs-label",
            ),

            *[
                html.Button(
                    label,
                    id=f"factor-{key}",
                    className=(
                        "factor-tab active"
                        if key == active_factor
                        else "factor-tab"
                    ),
                )
                for key, (_, label)
                in DRILLDOWN_FACTORS.items()
            ],
        ],
        className="factor-tabs",
    )


def drilldown_page(
    df: pd.DataFrame,
    factor_key: str,
) -> html.Div:

    if df.empty:
        return data_missing_page(
            "Drill-down Analysis"
        )

    factor_key = (
        factor_key
        if factor_key in DRILLDOWN_FACTORS
        else "wifi"
    )

    result = spearman_for_factor(
        df,
        factor_key,
    )

    rho_text = (
        f"{result['rho']:+.2f}"
        if result["rho"] is not None
        else "—"
    )

    p_text = (
        f"{result['p']:.3g}"
        if result["p"] is not None
        else "—"
    )

    if result["rho"] is None:
        strength = (
            "No stable monotonic relationship"
        )

    elif abs(result["rho"]) < 0.2:
        strength = "Very weak"

    elif abs(result["rho"]) < 0.4:
        strength = "Weak"

    elif abs(result["rho"]) < 0.7:
        strength = "Moderate"

    else:
        strength = "Strong"

    direction = (
        "positive"
        if result["rho"] is not None
        and result["rho"] > 0
        else
        "negative"
        if result["rho"] is not None
        else
        "undetermined"
    )

    return html.Div(
        [
            factor_tabs(
                factor_key
            ),

            html.Div(
                [
                    card(
                        [
                            html.Div(
                                [
                                    html.H3(
                                        f"{result['factor']} vs Overall Campus Experience",
                                        className="panel-title",
                                    ),

                                    html.Span(
                                        f"Spearman rank · n={result['n']}",
                                        className="panel-meta",
                                    ),
                                ],
                                className="panel-head",
                            ),

                            dcc.Graph(
                                figure=scatter_chart(
                                    result
                                ),
                                config={
                                    "displayModeBar": False
                                },
                                className="plotly-graph",
                            ),
                        ],
                        "panel-card chart-card drill-chart",
                    ),

                    card(
                        [
                            html.Div(
                                "STATISTICAL OUTPUT (RHO)",
                                className="stat-kicker",
                            ),

                            html.Div(
                                f"rₛ = {rho_text}",
                                className="rho-value",
                            ),

                            html.Div(
                                [
                                    html.Span(
                                        "p-value: "
                                    ),

                                    html.Strong(
                                        p_text
                                    ),

                                    html.Span(
                                        " · two-sided Spearman test"
                                    ),
                                ],
                                className="p-value",
                            ),

                            html.H4(
                                "Relationship Interpretation",
                                className="interpret-title",
                            ),

                            html.P(
                                f"Within the filtered responses, the rank "
                                f"correlation is {strength.lower()} and "
                                f"{direction} between "
                                f"{result['factor'].lower()} satisfaction "
                                f"and reported overall campus experience.",
                                className="panel-copy",
                            ),

                            html.P(
                                "Correlation does not establish causation. "
                                "The dashboard uses this relationship as a "
                                "drill-down signal for further discussion "
                                "rather than as a causal claim.",
                                className="panel-copy muted-copy",
                            ),
                        ],
                        "panel-card correlation-card",
                    ),
                ],
                className="content-grid drill-grid",
            ),
        ]
    )


# ============================================================
# RESPONSE EXPLORER
# ============================================================

def responses_page(
    df: pd.DataFrame,
    search: str = "",
) -> html.Div:

    if df.empty:
        return data_missing_page(
            "Response Explorer"
        )

    view = response_table(df)

    search = (
        search or ""
    ).strip().lower()

    if search:

        mask = (
            view.astype(str)
            .apply(
                lambda col:
                    col.str.lower().str.contains(
                        re.escape(search),
                        na=False,
                    )
            )
            .any(axis=1)
        )

        view = (
            view.loc[mask]
            .reset_index(drop=True)
        )

    table = dash_table.DataTable(
        id="responses-table",

        data=view.to_dict(
            "records"
        ),

        columns=[
            {
                "name": c,
                "id": c,
            }
            for c in view.columns
        ],

        page_current=0,
        page_size=25,
        page_action="native",
        sort_action="native",
        style_as_list_view=True,

        style_table={
            "overflowX": "auto",
            "maxHeight": "590px",
            "overflowY": "auto",
        },

        style_header={
            "backgroundColor": "#1d2432",
            "color": "#98a2b3",
            "fontWeight": "700",
            "fontSize": "10px",
            "textTransform": "uppercase",
            "letterSpacing": "0.06em",
            "border": "1px solid #263244",
            "padding": "10px",
        },

        style_cell={
            "backgroundColor": "#11151e",
            "color": "#d8dce4",
            "border": "1px solid #202a3a",
            "fontFamily": (
                "Inter, Segoe UI, Arial, sans-serif"
            ),
            "fontSize": "12px",
            "padding": "12px 10px",
            "height": "42px",
            "whiteSpace": "normal",
            "textAlign": "left",
        },

        style_cell_conditional=[
            {
                "if": {
                    "column_id": "ID"
                },
                "color": "#00e5ff",
                "fontWeight": "700",
                "width": "72px",
            },

            {
                "if": {
                    "column_id": "Satisfaction"
                },
                "color": "#2f80ed",
                "fontWeight": "700",
                "width": "90px",
            },

            {
                "if": {
                    "column_id": "Overall Exp"
                },
                "width": "120px",
            },
        ],

        style_data_conditional=[
            {
                "if": {
                    "filter_query":
                        '{Overall Exp} contains "Critical"'
                },
                "color": "#ff3b6b",
            },

            {
                "if": {
                    "filter_query":
                        '{Overall Exp} contains "Poor"'
                },
                "color": "#f59e0b",
            },
        ],
    )

    return html.Div(
        [
            html.Div(
                [
                    dcc.Input(
                        id={
                            "type": "response-search",
                            "index": "responses",
                        },
                        value=search,
                        placeholder=(
                            f"⌕  Search "
                            f"{len(response_table(df)):,} "
                            f"responses..."
                        ),
                        className="response-search",
                    ),

                    html.Button(
                        [
                            "⇩  Download Filtered Data (CSV)"
                        ],
                        id={
                            "type": "download-btn",
                            "index": "responses",
                        },
                        className="download-btn",
                    ),
                ],
                className="explorer-toolbar",
            ),

            card(
                [
                    html.Div(
                        [
                            html.H3(
                                "Responses Explorer",
                                className="panel-title",
                            ),

                            html.Span(
                                f"Showing {len(view):,} filtered rows",
                                className="panel-meta",
                            ),
                        ],
                        className="panel-head",
                    ),

                    table,
                ],
                "panel-card explorer-card",
            ),
        ]
    )


# ============================================================
# FEEDBACK
# ============================================================

def feedback_page(
    df: pd.DataFrame,
) -> html.Div:

    if df.empty:
        return data_missing_page(
            "Feedback"
        )

    records = feedback_records(
        df,
        limit=None,
    )

    return html.Div(
        [
            card(
                [
                    html.Div(
                        [
                            html.H3(
                                "Anonymous Student Feedback",
                                className="panel-title",
                            ),

                            html.Span(
                                f"{len(records)} written responses in current view",
                                className="panel-meta",
                            ),
                        ],
                        className="panel-head",
                    ),

                    html.Div(
                        [
                            html.Div(
                                [
                                    html.P(
                                        r["text"],
                                        className="feedback-text large",
                                    ),

                                    html.Div(
                                        f"{r['programme']} · Visit: {r['visit']}",
                                        className="feedback-meta",
                                    ),
                                ],
                                className="feedback-item",
                            )

                            for r in records
                        ]
                        or [
                            html.Div(
                                "No written feedback is available.",
                                className="empty-inline",
                            )
                        ],

                        className=(
                            "feedback-list feedback-full"
                        ),
                    ),
                ],
                "panel-card",
            )
        ]
    )


# ============================================================
# APP LAYOUT
# ============================================================

def app_layout() -> html.Div:

    return html.Div(
        [
            dcc.Location(
                id="url",
                refresh=False,
            ),

            dcc.Store(
                id="dataset-store",
                data=None,
            ),

            dcc.Store(
                id="staged-upload-store",
                data=None,
            ),

            dcc.Store(
                id="active-filters-store",
                data=FILTER_DEFAULTS,
            ),

            dcc.Store(
                id="dataset-meta-store",
                data={
                    "active": False
                },
            ),

            dcc.Store(
                id="refresh-store",
                data=0,
            ),

            dcc.Store(
                id="drilldown-factor-store",
                data="wifi",
            ),

            # FIX:
            # Persistent store for Response Explorer search.
            # The search box itself is dynamically generated.
            dcc.Store(
                id="response-search-store",
                data="",
            ),

            dcc.Interval(
                id="live-interval",
                interval=30000,
                n_intervals=0,
            ),

            dcc.Download(
                id="download-csv"
            ),

            sidebar(),

            mobile_header(),

            html.Div(
                [
                    header(),

                    filter_bar(),

                    status_line(),

                    html.Main(
                        id="page-content",
                        className="page-content",
                    ),
                ],
                className="main-shell",
            ),

            # =================================================
            # UPLOAD MODAL
            # =================================================

            html.Div(
                [
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Div(
                                        "▣",
                                        className="modal-icon",
                                    ),

                                    html.Div(
                                        [
                                            html.H3(
                                                "Upload New Survey Dataset",
                                                className="modal-title",
                                            ),

                                            html.P(
                                                "Ingest student feedback files exported "
                                                "from Google Forms/Sheets",
                                                className="modal-subtitle",
                                            ),
                                        ],
                                        className="modal-copy",
                                    ),
                                ],
                                className="modal-header-row",
                            ),

                            html.Div(
                                className="modal-divider"
                            ),

                            dcc.Upload(
                                id="dataset-upload",

                                children=html.Div(
                                    [
                                        html.Div(
                                            "⌁",
                                            className="drop-icon",
                                        ),

                                        html.Div(
                                            "Drag & drop CSV / XLSX files here",
                                            className="drop-title",
                                        ),

                                        html.Div(
                                            "or click to browse local folders",
                                            className="drop-subtitle",
                                        ),
                                    ],
                                    className="dropzone-content",
                                ),

                                accept=(
                                    ".csv,.xlsx,.xls,"
                                    "text/csv,"
                                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,"
                                    "application/vnd.ms-excel"
                                ),

                                multiple=False,

                                className="upload-dropzone",
                            ),

                            html.Div(
                                id="upload-status-area",
                                className="upload-status-area",
                            ),

                            html.Div(
                                id="upload-mapping-area",
                                className="upload-mapping-area",
                            ),

                            html.Div(
                                [
                                    html.Button(
                                        "Cancel",
                                        id="upload-cancel",
                                        className="secondary-btn",
                                    ),

                                    html.Button(
                                        "Deploy & Use Dataset",
                                        id="deploy-dataset",
                                        className="primary-btn",
                                        disabled=True,
                                    ),
                                ],
                                className="modal-actions",
                            ),
                        ],
                        className="modal-card",
                    )
                ],
                id="upload-modal",
                className="modal-backdrop hidden",
            ),
        ],
        className="app-root",
    )


app.layout = app_layout


# ============================================================
# NAVIGATION CALLBACKS
# ============================================================

@app.callback(
    [
        Output(
            f"nav-{label.lower().replace(' ', '-').replace('/', '-')}",
            "className",
        )
        for _, label, _ in NAV_ITEMS
    ],
    Input(
        "url",
        "pathname",
    ),
)
def set_active_nav(pathname):

    path = pathname or "/overview"

    return tuple(
        "nav-link active"
        if path == href
        else "nav-link"
        for href, _, _ in NAV_ITEMS
    )


@app.callback(
    Output(
        "mobile-nav",
        "value",
    ),
    Input(
        "url",
        "pathname",
    ),
)
def sync_mobile_nav(pathname):

    return (
        pathname
        if pathname in [x[0] for x in NAV_ITEMS]
        else "/overview"
    )


@app.callback(
    Output(
        "url",
        "pathname",
        allow_duplicate=True,
    ),
    Input(
        "mobile-nav",
        "value",
    ),
    prevent_initial_call=True,
)
def mobile_navigation(value):

    return value or "/overview"


# ============================================================
# FILTER OPTIONS
# ============================================================

@app.callback(
    Output(
        "filters-container",
        "style",
    ),

    Output(
        "filter-age",
        "options",
    ),

    Output(
        "filter-age",
        "value",
    ),

    Output(
        "filter-gender",
        "options",
    ),

    Output(
        "filter-gender",
        "value",
    ),

    Output(
        "filter-programme",
        "options",
    ),

    Output(
        "filter-programme",
        "value",
    ),

    Output(
        "filter-visit",
        "options",
    ),

    Output(
        "filter-visit",
        "value",
    ),

    Input(
        "dataset-store",
        "data",
    ),
)
def update_filter_options(data_json):

    if not data_json:

        return (
            {"display": "none"},
            [],
            "__all__",
            [],
            "__all__",
            [],
            "__all__",
            [],
            "__all__",
        )

    df = dataframe_from_json(
        data_json
    )

    def opts(
        column,
        all_label,
    ):

        values = [
            v
            for v in
            df[column]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
            if v
        ]

        values.sort()

        return (
            [
                {
                    "label": all_label,
                    "value": "__all__",
                }
            ]
            +
            [
                {
                    "label": v,
                    "value": v,
                }
                for v in values
            ]
        )

    return (
        {"display": "flex"},

        opts(
            "age_group",
            "All Ages",
        ),

        "__all__",

        opts(
            "gender",
            "All Genders",
        ),

        "__all__",

        opts(
            "programme",
            "All Programmes",
        ),

        "__all__",

        opts(
            "visit_frequency",
            "All Frequencies",
        ),

        "__all__",
    )


# ============================================================
# ACTIVE FILTERS
# ============================================================

@app.callback(
    Output(
        "active-filters-store",
        "data",
    ),

    Output(
        "filter-age",
        "value",
        allow_duplicate=True,
    ),

    Output(
        "filter-gender",
        "value",
        allow_duplicate=True,
    ),

    Output(
        "filter-programme",
        "value",
        allow_duplicate=True,
    ),

    Output(
        "filter-visit",
        "value",
        allow_duplicate=True,
    ),

    Input(
        "apply-filters",
        "n_clicks",
    ),

    Input(
        "reset-filters",
        "n_clicks",
    ),

    State(
        "filter-age",
        "value",
    ),

    State(
        "filter-gender",
        "value",
    ),

    State(
        "filter-programme",
        "value",
    ),

    State(
        "filter-visit",
        "value",
    ),

    prevent_initial_call=True,
)
def set_active_filters(
    _apply,
    _reset,
    age,
    gender,
    programme,
    visit,
):

    trigger = ctx.triggered_id

    if trigger == "reset-filters":

        return (
            FILTER_DEFAULTS,
            "__all__",
            "__all__",
            "__all__",
            "__all__",
        )

    return (
        {
            "age": age or "__all__",
            "gender": gender or "__all__",
            "programme": programme or "__all__",
            "visit": visit or "__all__",
        },

        no_update,
        no_update,
        no_update,
        no_update,
    )


# ============================================================
# FILTER STATUS
# ============================================================

@app.callback(
    Output(
        "filter-status",
        "children",
    ),

    Input(
        "dataset-store",
        "data",
    ),

    Input(
        "active-filters-store",
        "data",
    ),

    Input(
        "refresh-store",
        "data",
    ),

    Input(
        "live-interval",
        "n_intervals",
    ),
)
def update_filter_status(
    data_json,
    filters,
    _refresh,
    _interval,
):

    if not data_json:
        return ""

    df = dataframe_from_json(
        data_json
    )

    view = apply_filters(
        df,
        filters or FILTER_DEFAULTS,
    )

    active_bits = [
        v
        for v in (filters or {}).values()
        if v and v != "__all__"
    ]

    text = (
        f"Live batch status · "
        f"{len(view):,} of "
        f"{len(df):,} responses visible"
    )

    if active_bits:

        text += (
            " · Filters applied across "
            "all dashboard views"
        )

    else:

        text += (
            " · Showing the complete "
            "uploaded dataset"
        )

    return [
        html.Span(
            "•",
            className="status-line-dot",
        ),
        text,
    ]


# ============================================================
# DATASET STATUS / HEADER
# ============================================================

@app.callback(
    Output(
        "page-title",
        "children",
    ),

    Output(
        "dataset-badge-text",
        "children",
    ),

    Output(
        "page-subtitle",
        "children",
    ),

    Output(
        "sidebar-dataset-status",
        "children",
    ),

    Output(
        "sidebar-dataset-meta",
        "children",
    ),

    Output(
        "dataset-dot",
        "className",
    ),

    Input(
        "url",
        "pathname",
    ),

    Input(
        "dataset-meta-store",
        "data",
    ),

    Input(
        "live-interval",
        "n_intervals",
    ),
)
def update_dataset_status(
    pathname,
    meta,
    _interval,
):

    titles = {
        "/overview":
            "Campus Life & Student Satisfaction Analytics",

        "/satisfaction":
            "Satisfaction Analytics",

        "/issues":
            "Campus Issues & Priorities",

        "/drilldown":
            "Drill-down Factor Correlation",

        "/responses":
            "Response Explorer",

        "/feedback":
            "Anonymous Student Feedback",
    }

    title = titles.get(
        pathname or "/overview",
        "Campus Life & Student Satisfaction Analytics",
    )

    meta = meta or {}

    if not meta.get("active"):

        return (
            title,

            "Static Dashboard",

            "Dashboard ready for Google Forms "
            "CSV/XLSX batch ingestion",

            "No Active Data",

            "Please upload survey feedback",

            "status-dot offline",
        )

    rows = meta.get(
        "rows",
        0,
    )

    filename = meta.get(
        "filename",
        "uploaded dataset",
    )

    refreshed = meta.get(
        "refreshed_at",
        "",
    )

    return (
        title,

        "Live Dataset",

        f"Python Dash backend synchronized · "
        f"{filename}",

        f"{rows:,} responses",

        f"Batch refreshed {refreshed}",

        "status-dot",
    )


# ============================================================
# REFRESH
# ============================================================

@app.callback(
    Output(
        "refresh-store",
        "data",
    ),

    Input(
        "refresh-btn",
        "n_clicks",
    ),

    State(
        "refresh-store",
        "data",
    ),

    State(
        "dataset-meta-store",
        "data",
    ),

    prevent_initial_call=True,
)
def refresh_data(
    n_clicks,
    current,
    meta,
):

    if not n_clicks:
        raise PreventUpdate

    return (
        current or 0
    ) + 1


# ============================================================
# UPLOAD MODAL
# ============================================================

@app.callback(
    Output(
        "upload-modal",
        "className",
    ),

    Input(
        "header-upload-btn",
        "n_clicks",
    ),

    Input(
        "sidebar-upload-btn",
        "n_clicks",
    ),

    Input(
        "empty-upload-btn",
        "n_clicks",
        allow_optional=True,
    ),

    Input(
        "upload-cancel",
        "n_clicks",
    ),

    prevent_initial_call=True,
)
def toggle_upload_modal(
    _header,
    _sidebar,
    _empty,
    _cancel,
):

    trigger = ctx.triggered_id

    if trigger == "upload-cancel":

        return "modal-backdrop hidden"

    return "modal-backdrop"


# ============================================================
# STAGE DATASET
# ============================================================

@app.callback(
    Output(
        "upload-status-area",
        "children",
    ),

    Output(
        "upload-mapping-area",
        "children",
    ),

    Output(
        "staged-upload-store",
        "data",
    ),

    Output(
        "deploy-dataset",
        "disabled",
    ),

    Input(
        "dataset-upload",
        "contents",
    ),

    State(
        "dataset-upload",
        "filename",
    ),

    prevent_initial_call=True,
)
def stage_uploaded_dataset(
    contents,
    filename,
):

    if not contents or not filename:
        raise PreventUpdate

    try:

        df, report, mapping = load_uploaded_contents(
            contents,
            filename,
        )

    except Exception as exc:

        msg = html.Div(
            [
                html.Span(
                    "×",
                    className="status-error-dot",
                ),

                html.Div(
                    [
                        html.Strong(
                            "Upload failed"
                        ),

                        html.Div(
                            str(exc)
                        ),
                    ]
                ),
            ],
            className="upload-error",
        )

        return (
            msg,
            "",
            None,
            True,
        )

    if not report.ok:

        missing = (
            ", ".join(
                f"Q{q}"
                for q in (
                    report.missing_questions
                    or []
                )
            )
            or "invalid values"
        )

        msg = html.Div(
            [
                html.Span(
                    "×",
                    className="status-error-dot",
                ),

                html.Div(
                    [
                        html.Strong(
                            "Invalid Survey Format"
                        ),

                        html.Div(
                            f"{report.message} "
                            f"· Check: {missing}"
                        ),
                    ]
                ),
            ],
            className="upload-error",
        )

        return (
            msg,
            "",
            None,
            True,
        )

    warnings = (
        ""
        if not report.warnings
        else html.Div(
            [
                html.Div(
                    " · ".join(
                        report.warnings
                    ),
                    className="upload-warning-text",
                )
            ],
            className="upload-warning",
        )
    )

    status = html.Div(
        [
            html.Div(
                [
                    html.Span(
                        "●",
                        className="status-good-dot",
                    ),

                    html.Strong(
                        f"{filename} uploaded successfully"
                    ),
                ],
                className="upload-success-title",
            ),

            html.Div(
                [
                    html.Div(
                        [
                            html.Span(
                                "ROWS DETECTED"
                            ),

                            html.Strong(
                                f"{report.row_count:,} entries"
                            ),
                        ]
                    ),

                    html.Div(
                        [
                            html.Span(
                                "COLUMNS MAPPED"
                            ),

                            html.Strong(
                                f"{report.mapped_fields} questions"
                            ),
                        ]
                    ),

                    html.Div(
                        [
                            html.Span(
                                "STATUS"
                            ),

                            html.Strong(
                                "Valid Survey Format"
                            ),
                        ]
                    ),
                ],
                className="upload-stat-grid",
            ),

            warnings,
        ],
        className="upload-success",
    )

    mapping_labels = [
        f"{FRIENDLY_NAMES.get(k, k)}"
        for k in mapping.keys()
    ]

    mapping_text = (
        ", ".join(
            mapping_labels
        )
    )

    mapping_area = html.Div(
        [
            html.Div(
                "MAPPED SYSTEM COLUMNS",
                className="mapping-title",
            ),

            html.Div(
                mapping_text,
                className="mapping-copy",
            ),
        ],
        className="mapping-box",
    )

    staged = {
        "data": dataframe_to_json(
            df
        ),

        "filename": filename,

        "report": report.to_dict(),
    }

    return (
        status,
        mapping_area,
        staged,
        False,
    )


# ============================================================
# DEPLOY DATASET
# ============================================================

@app.callback(
    Output(
        "dataset-store",
        "data",
    ),

    Output(
        "dataset-meta-store",
        "data",
    ),

    Output(
        "upload-modal",
        "className",
        allow_duplicate=True,
    ),

    Input(
        "deploy-dataset",
        "n_clicks",
    ),

    State(
        "staged-upload-store",
        "data",
    ),

    prevent_initial_call=True,
)
def deploy_dataset(
    n_clicks,
    staged,
):

    if not n_clicks or not staged:
        raise PreventUpdate

    df_json = staged["data"]

    df = dataframe_from_json(
        df_json
    )

    now = datetime.now().strftime(
        "%Y-%m-%d %H:%M"
    )

    meta = {
        "active": True,
        "filename": staged.get(
            "filename",
            "uploaded dataset",
        ),
        "rows": len(df),
        "refreshed_at": now,
    }

    return (
        df_json,
        meta,
        "modal-backdrop hidden",
    )


# ============================================================
# MAIN PAGE RENDERER
# ============================================================
#
# IMPORTANT FIXES:
#
# 1. response-search is NOT directly used here anymore.
#    The dynamic search box writes into response-search-store.
#
# 2. No dataset is handled safely before dataframe_from_json().
#
# 3. Exceptions are caught so Dash doesn't only show:
#       Callback error updating page-content.children
#
# ============================================================

@app.callback(
    Output(
        "page-content",
        "children",
    ),

    Input(
        "url",
        "pathname",
    ),

    Input(
        "dataset-store",
        "data",
    ),

    Input(
        "active-filters-store",
        "data",
    ),

    Input(
        "drilldown-factor-store",
        "data",
    ),

    Input(
        "response-search-store",
        "data",
    ),

    Input(
        "refresh-store",
        "data",
    ),

    Input(
        "live-interval",
        "n_intervals",
    ),
)
def render_page(
    pathname,
    data_json,
    filters,
    factor_key,
    search,
    _refresh,
    _interval,
):

    pathname = (
        pathname
        or "/overview"
    )

    try:

        # -----------------------------------------------
        # NO DATA
        # -----------------------------------------------

        if not data_json:

            if pathname == "/overview":
                return placeholder_overview()

            section_titles = {
                "/satisfaction":
                    "Satisfaction Analytics",

                "/issues":
                    "Campus Issues",

                "/drilldown":
                    "Drill-down Analysis",

                "/responses":
                    "Response Explorer",

                "/feedback":
                    "Feedback",
            }

            return data_missing_page(
                section_titles.get(
                    pathname,
                    "Dashboard",
                )
            )

        # -----------------------------------------------
        # RECONSTRUCT DATAFRAME
        # -----------------------------------------------

        df = dataframe_from_json(
            data_json
        )

        if df is None or df.empty:

            if pathname == "/overview":
                return placeholder_overview()

            section_titles = {
                "/satisfaction":
                    "Satisfaction Analytics",

                "/issues":
                    "Campus Issues",

                "/drilldown":
                    "Drill-down Analysis",

                "/responses":
                    "Response Explorer",

                "/feedback":
                    "Feedback",
            }

            return data_missing_page(
                section_titles.get(
                    pathname,
                    "Dashboard",
                )
            )

        # -----------------------------------------------
        # APPLY FILTERS
        # -----------------------------------------------

        view = apply_filters(
            df,
            filters or FILTER_DEFAULTS,
        )

        # -----------------------------------------------
        # PAGE ROUTING
        # -----------------------------------------------

        if pathname == "/overview":

            return overview_page(
                view
            )

        if pathname == "/satisfaction":

            return satisfaction_page(
                view
            )

        if pathname == "/issues":

            return issues_page(
                view
            )

        if pathname == "/drilldown":

            return drilldown_page(
                view,
                factor_key or "wifi",
            )

        if pathname == "/responses":

            return responses_page(
                view,
                search or "",
            )

        if pathname == "/feedback":

            return feedback_page(
                view
            )

        return overview_page(
            view
        )

    except Exception as exc:

        # Print complete traceback in VS Code terminal.
        import traceback

        traceback.print_exc()

        # Show useful error in the dashboard rather than
        # only the generic Dash callback error.

        return html.Div(
            [
                html.Div(
                    "⚠",
                    className="empty-icon small",
                ),

                html.H2(
                    "This dashboard view could not be rendered",
                    className="empty-title",
                ),

                html.P(
                    f"Path: {pathname}",
                    className="empty-copy",
                ),

                html.Pre(
                    f"{type(exc).__name__}: {exc}",
                    className="error-detail",
                ),

                html.P(
                    "Open the VS Code terminal to see the full traceback.",
                    className="empty-copy",
                ),
            ],
            className="empty-panel page-empty",
        )


# ============================================================
# RESPONSE SEARCH STORE
# ============================================================
#
# FIX:
# The search input is dynamically created only on the
# Response Explorer page. This callback copies its value
# into a permanent dcc.Store.
#
# allow_optional=True prevents Dash from raising a
# nonexistent-object error on the other pages.
# ============================================================

@app.callback(
    Output(
        "response-search-store",
        "data",
    ),

    Input(
        {
            "type": "response-search",
            "index": "responses",
        },
        "value",
        allow_optional=True,
    ),

    prevent_initial_call=True,
)
def sync_response_search(
    value,
):

    return value or ""


# ============================================================
# DRILL DOWN FACTOR
# ============================================================

@app.callback(
    Output(
        "drilldown-factor-store",
        "data",
    ),

    Input(
        "factor-wifi",
        "n_clicks",
        allow_optional=True,
    ),

    Input(
        "factor-seating",
        "n_clicks",
        allow_optional=True,
    ),

    Input(
        "factor-food",
        "n_clicks",
        allow_optional=True,
    ),

    Input(
        "factor-learning",
        "n_clicks",
        allow_optional=True,
    ),

    prevent_initial_call=True,
)
def select_factor(
    _wifi,
    _seating,
    _food,
    _learning,
):

    trigger = (
        ctx.triggered_id
        or "factor-wifi"
    )

    return trigger.replace(
        "factor-",
        "",
    )


# ============================================================
# DOWNLOAD FILTERED DATA
# ============================================================
#
# FIX:
# The Download button is dynamically created only on the
# Response Explorer page, so the callback now uses a matching
# dictionary ID + allow_optional=True.
# ============================================================

@app.callback(
    Output(
        "download-csv",
        "data",
    ),

    Input(
        {
            "type": "download-btn",
            "index": "responses",
        },
        "n_clicks",
        allow_optional=True,
    ),

    State(
        "dataset-store",
        "data",
    ),

    State(
        "active-filters-store",
        "data",
    ),

    State(
        "response-search-store",
        "data",
    ),

    prevent_initial_call=True,
)
def download_filtered(
    n_clicks,
    data_json,
    filters,
    search,
):

    if not n_clicks or not data_json:
        raise PreventUpdate

    df = apply_filters(
        dataframe_from_json(
            data_json
        ),
        filters,
    )

    table = response_table(
        df
    )

    search = (
        search or ""
    ).strip().lower()

    if search:

        mask = (
            table.astype(str)
            .apply(
                lambda col:
                    col.str.lower()
                    .str.contains(
                        re.escape(search),
                        na=False,
                    )
            )
            .any(axis=1)
        )

        table = table.loc[
            mask
        ]

    return dcc.send_data_frame(
        table.to_csv,
        "campus_satisfaction_filtered.csv",
        index=False,
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=True,
        host="127.0.0.1",
        port=8050,
    )