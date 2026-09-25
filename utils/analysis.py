from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from .data_processing import FRIENDLY_NAMES

SATISFACTION_FIELDS = [
    ("wifi_satisfaction", "Wi-Fi Quality"),
    ("classroom_satisfaction", "Classrooms"),
    ("computer_lab_satisfaction", "Computer Laboratories"),
    ("bathroom_satisfaction", "Campus Bathrooms"),
    ("campus_cleanliness_satisfaction", "Campus Cleanliness"),
    ("seating_satisfaction", "Seating / Common Areas"),
    ("learning_resources_satisfaction", "Learning Resources"),
    ("canteen_facilities_satisfaction", "Canteen Facilities"),
    ("canteen_food_satisfaction", "Canteen Food Quality"),
    ("student_admin_satisfaction", "Student / Administrative Services"),
    ("campus_events_satisfaction", "Campus Events / Activities"),
    ("campus_environment_satisfaction", "Campus Environment"),
]

DRILLDOWN_FACTORS = {
    "wifi": ("wifi_satisfaction", "Campus Wi-Fi"),
    "seating": ("seating_satisfaction", "Seating / Common Areas"),
    "food": ("canteen_food_satisfaction", "Canteen Food Quality"),
    "learning": ("learning_resources_satisfaction", "Learning Resources"),
}

MOBILE_ORDER = ["Always", "Often", "Sometimes", "Rarely", "Never"]


def apply_filters(df: pd.DataFrame, filters: dict[str, Any] | None) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    filters = filters or {}
    out = df.copy()
    field_map = {
        "age": "age_group",
        "gender": "gender",
        "programme": "programme",
        "visit": "visit_frequency",
    }
    for filter_key, column in field_map.items():
        value = filters.get(filter_key)
        if value and value != "__all__":
            out = out[out[column].astype("string") == str(value)]
    return out


def kpis(df: pd.DataFrame) -> dict[str, Any]:
    n = len(df)
    overall = pd.to_numeric(df.get("overall_experience_satisfaction"), errors="coerce")
    valid = overall.dropna()
    mean = float(valid.mean()) if not valid.empty else None
    low_rate = float((valid < 3).mean() * 100) if not valid.empty else None

    counts = improvement_counts(df)
    critical = counts.iloc[0]["area"] if not counts.empty else "—"
    critical_count = int(counts.iloc[0]["responses"]) if not counts.empty else 0
    return {
        "responses": n,
        "mean": mean,
        "mean_n": int(valid.shape[0]),
        "low_rate": low_rate,
        "critical": critical,
        "critical_count": critical_count,
    }


def score_distribution(df: pd.DataFrame) -> pd.DataFrame:
    scores = pd.to_numeric(df["overall_experience_satisfaction"], errors="coerce")
    counts = scores.value_counts().reindex([5, 4, 3, 2, 1], fill_value=0).astype(int)
    labels = {5: "Excellent (5/5)", 4: "Good (4/5)", 3: "Moderate (3/5)", 2: "Poor (2/5)", 1: "Critical (1/5)"}
    total = counts.sum()
    return pd.DataFrame(
        {
            "score": counts.index,
            "label": [labels[int(x)] for x in counts.index],
            "count": counts.values,
            "pct": [float(v / total * 100) if total else 0 for v in counts.values],
        }
    )


def satisfaction_means(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for field, label in SATISFACTION_FIELDS + [("overall_experience_satisfaction", "Overall Experience")]:
        value = pd.to_numeric(df[field], errors="coerce").mean()
        rows.append({"field": field, "label": label, "mean": value})
    return pd.DataFrame(rows).dropna(subset=["mean"])


def programme_heatmap(df: pd.DataFrame) -> pd.DataFrame:
    focus = [
        ("wifi_satisfaction", "Wi-Fi Quality"),
        ("seating_satisfaction", "Seating / Common Areas"),
        ("canteen_food_satisfaction", "Canteen Food Quality"),
        ("learning_resources_satisfaction", "Learning Resources"),
        ("overall_experience_satisfaction", "Overall Experience"),
    ]
    programmes = sorted(df["programme"].dropna().astype(str).unique().tolist())
    if not programmes:
        return pd.DataFrame()
    data = {}
    for field, label in focus:
        data[label] = [pd.to_numeric(df.loc[df["programme"] == p, field], errors="coerce").mean() for p in programmes]
    return pd.DataFrame(data, index=programmes).T


def _split_multi(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df:
        return pd.Series(dtype="string")
    items: list[str] = []
    for value in df[column].dropna().astype(str):
        if not value.strip():
            continue
        seen: set[str] = set()
        for part in value.split(","):
            item = " ".join(part.strip().split())
            if item and item not in seen:
                items.append(item)
                seen.add(item)
    return pd.Series(items, dtype="string")


def improvement_counts(df: pd.DataFrame) -> pd.DataFrame:
    series = _split_multi(df, "improvement_areas")
    if series.empty:
        return pd.DataFrame(columns=["area", "responses", "pct"])
    counts = series.value_counts().rename_axis("area").reset_index(name="responses")
    counts["pct"] = counts["responses"] / max(len(df), 1) * 100
    return counts.sort_values(["responses", "area"], ascending=[False, True]).reset_index(drop=True)


def mobile_reason_counts(df: pd.DataFrame) -> pd.DataFrame:
    series = _split_multi(df, "mobile_data_reasons")
    if series.empty:
        return pd.DataFrame(columns=["reason", "responses", "pct"])
    counts = series.value_counts().rename_axis("reason").reset_index(name="responses")
    counts["pct"] = counts["responses"] / max(len(df), 1) * 100
    return counts.sort_values(["responses", "reason"], ascending=[False, True]).reset_index(drop=True)


def mobile_frequency_counts(df: pd.DataFrame) -> pd.DataFrame:
    counts = df["mobile_data_frequency"].dropna().astype(str).value_counts().reindex(MOBILE_ORDER, fill_value=0)
    out = pd.DataFrame({"frequency": counts.index, "responses": counts.values.astype(int)})
    out["pct"] = out["responses"] / max(out["responses"].sum(), 1) * 100
    return out


def programme_overall_means(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["programme", "mean"])
    out = (
        df.assign(_overall=pd.to_numeric(df["overall_experience_satisfaction"], errors="coerce"))
        .groupby("programme", dropna=True)["_overall"]
        .mean()
        .dropna()
        .sort_values(ascending=False)
        .rename("mean")
        .reset_index()
    )
    return out


def visit_overall_means(df: pd.DataFrame) -> pd.DataFrame:
    order = ["Every day", "3–4 days a week", "1–2 days a week", "Occasionally", "Rarely"]
    out = (
        df.assign(_overall=pd.to_numeric(df["overall_experience_satisfaction"], errors="coerce"))
        .groupby("visit_frequency", dropna=True)["_overall"]
        .mean()
        .dropna()
        .reindex(order)
        .dropna()
        .rename("mean")
        .reset_index()
    )
    return out


def spearman_for_factor(df: pd.DataFrame, factor_key: str) -> dict[str, Any]:
    field, label = DRILLDOWN_FACTORS[factor_key]
    x = pd.to_numeric(df[field], errors="coerce")
    y = pd.to_numeric(df["overall_experience_satisfaction"], errors="coerce")
    paired = pd.DataFrame({"x": x, "y": y}).dropna()
    if len(paired) < 3 or paired["x"].nunique() < 2 or paired["y"].nunique() < 2:
        return {"factor": label, "n": len(paired), "rho": None, "p": None, "data": paired}
    result = spearmanr(paired["x"], paired["y"])
    return {"factor": label, "n": len(paired), "rho": float(result.statistic), "p": float(result.pvalue), "data": paired}


def response_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["ID", "Demographics", "Campus Visit", "Satisfaction", "Overall Exp", "Improvement Area", "Mobile Data"])
    out = pd.DataFrame()
    out["ID"] = df["response_id"]
    out["Demographics"] = df["age_group"].fillna("—").astype(str) + " · " + df["gender"].fillna("—").astype(str) + " · " + df["programme"].fillna("—").astype(str)
    out["Campus Visit"] = df["visit_frequency"].fillna("—")
    sat = pd.to_numeric(df["overall_experience_satisfaction"], errors="coerce")
    out["Satisfaction"] = sat.map(lambda v: f"{int(v)}/5" if pd.notna(v) else "—")
    labels = {1: "Critical (1/5)", 2: "Poor (2/5)", 3: "Moderate (3/5)", 4: "Good (4/5)", 5: "Excellent (5/5)"}
    out["Overall Exp"] = sat.map(lambda v: labels.get(int(v), "—") if pd.notna(v) else "—")
    out["Improvement Area"] = df["improvement_areas"].replace("", "—")
    out["Mobile Data"] = df["mobile_data_frequency"].fillna("—")
    return out


def feedback_records(df: pd.DataFrame, limit: int | None = None) -> list[dict[str, Any]]:
    if df.empty:
        return []
    view = df.copy()
    if "timestamp" in view:
        view = view.sort_values("timestamp", ascending=False, na_position="last")
    records = []
    for _, row in view.iterrows():
        text = str(row.get("feedback", "")).strip()
        if not text or text.lower() in {"nan", "none", "no"}:
            continue
        programme = row.get("programme")
        visit = row.get("visit_frequency")
        programme = "—" if pd.isna(programme) or not str(programme).strip() else str(programme)
        visit = "—" if pd.isna(visit) or not str(visit).strip() else str(visit)
        records.append(
            {
                "text": text,
                "programme": programme,
                "visit": visit,
                "timestamp": row.get("timestamp"),
            }
        )
        if limit and len(records) >= limit:
            break
    return records
