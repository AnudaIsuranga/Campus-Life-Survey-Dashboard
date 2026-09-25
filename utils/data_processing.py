from __future__ import annotations

import base64
import io
import re
import unicodedata
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd


CANONICAL_FIELDS = [
    "timestamp",
    "age_group",
    "gender",
    "programme",
    "visit_frequency",
    "wifi_satisfaction",
    "classroom_satisfaction",
    "computer_lab_satisfaction",
    "bathroom_satisfaction",
    "campus_cleanliness_satisfaction",
    "seating_satisfaction",
    "learning_resources_satisfaction",
    "canteen_facilities_satisfaction",
    "canteen_food_satisfaction",
    "student_admin_satisfaction",
    "campus_events_satisfaction",
    "campus_environment_satisfaction",
    "overall_experience_satisfaction",
    "improvement_areas",
    "mobile_data_frequency",
    "mobile_data_reasons",
    "feedback",
]

QUESTION_TO_CANONICAL = {
    1: "age_group",
    2: "gender",
    3: "programme",
    4: "visit_frequency",
    5: "wifi_satisfaction",
    6: "classroom_satisfaction",
    7: "computer_lab_satisfaction",
    8: "bathroom_satisfaction",
    9: "campus_cleanliness_satisfaction",
    10: "seating_satisfaction",
    11: "learning_resources_satisfaction",
    12: "canteen_facilities_satisfaction",
    13: "canteen_food_satisfaction",
    14: "student_admin_satisfaction",
    15: "campus_events_satisfaction",
    16: "campus_environment_satisfaction",
    17: "overall_experience_satisfaction",
    18: "improvement_areas",
    19: "mobile_data_frequency",
    20: "mobile_data_reasons",
    21: "feedback",
}

REQUIRED_QUESTIONS = list(range(1, 21))

NUMERIC_FIELDS = [
    v for q, v in QUESTION_TO_CANONICAL.items()
    if 5 <= q <= 17
]

FRIENDLY_NAMES = {
    "timestamp": "Timestamp",
    "age_group": "Age Group",
    "gender": "Gender",
    "programme": "Programme",
    "visit_frequency": "Visit Frequency",
    "wifi_satisfaction": "Campus Wi-Fi",
    "classroom_satisfaction": "Classrooms",
    "computer_lab_satisfaction": "Computer Laboratories",
    "bathroom_satisfaction": "Campus Bathrooms",
    "campus_cleanliness_satisfaction": "Campus Cleanliness",
    "seating_satisfaction": "Seating / Common Areas",
    "learning_resources_satisfaction": "Learning Resources",
    "canteen_facilities_satisfaction": "Canteen Facilities",
    "canteen_food_satisfaction": "Canteen Food Quality",
    "student_admin_satisfaction": "Student / Administrative Services",
    "campus_events_satisfaction": "Campus Events / Activities",
    "campus_environment_satisfaction": "Campus Environment",
    "overall_experience_satisfaction": "Overall Campus Experience",
    "improvement_areas": "Improvement Areas",
    "mobile_data_frequency": "Personal Mobile Data Frequency",
    "mobile_data_reasons": "Mobile Data / Hotspot Reasons",
    "feedback": "Student Feedback",
}


@dataclass
class ValidationReport:
    ok: bool
    message: str
    row_count: int = 0
    mapped_fields: int = 0
    missing_questions: list[int] | None = None
    invalid_numeric: dict[str, int] | None = None
    missing_value_counts: dict[str, int] | None = None
    duplicate_rows: int = 0
    warnings: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _norm_header(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value))
    text = text.replace("\u00a0", " ").strip()
    return re.sub(r"\s+", " ", text)


def question_number(header: Any) -> int | None:
    text = _norm_header(header)
    match = re.match(r"^\s*(\d+)\s*[.)]?", text)
    return int(match.group(1)) if match else None


def _read_dataframe(contents: str, filename: str) -> pd.DataFrame:
    if "," not in contents:
        raise ValueError(
            "The uploaded file payload is not a valid Dash upload."
        )

    _, encoded = contents.split(",", 1)
    raw = base64.b64decode(encoded)

    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    if ext == "csv":
        for encoding in (
            "utf-8-sig",
            "utf-8",
            "cp1252",
            "latin-1",
        ):
            try:
                return pd.read_csv(
                    io.BytesIO(raw),
                    encoding=encoding
                )
            except UnicodeDecodeError:
                continue

        raise ValueError(
            "The CSV could not be decoded as text."
        )

    if ext in {"xlsx", "xls"}:
        return pd.read_excel(io.BytesIO(raw))

    raise ValueError(
        "Unsupported file type. Please upload CSV, XLSX, or XLS."
    )


def _clean_text(series: pd.Series) -> pd.Series:
    return (
        series.astype("string")
        .str.strip()
        .replace(
            {
                "<NA>": pd.NA,
                "nan": pd.NA,
                "None": pd.NA,
            }
        )
    )


def _clean_multiselect(value: Any) -> str:
    if pd.isna(value):
        return ""

    items = []

    for piece in str(value).replace("\u00a0", " ").split(","):
        item = re.sub(r"\s+", " ", piece).strip()

        if item and item not in items:
            items.append(item)

    return ", ".join(items)


def _column_mapping(
    raw_df: pd.DataFrame
) -> tuple[dict[str, str], list[int]]:

    q_to_col: dict[int, str] = {}

    for col in raw_df.columns:
        q = question_number(col)

        if q is not None and q not in q_to_col:
            q_to_col[q] = col

    mapping: dict[str, str] = {}

    for q, canonical in QUESTION_TO_CANONICAL.items():
        if q in q_to_col:
            mapping[canonical] = q_to_col[q]

    missing = [
        q for q in REQUIRED_QUESTIONS
        if q not in q_to_col
    ]

    return mapping, missing


def prepare_dataframe(
    raw_df: pd.DataFrame
) -> tuple[pd.DataFrame, ValidationReport, dict[str, str]]:

    if raw_df is None or raw_df.empty:
        return (
            pd.DataFrame(),
            ValidationReport(
                False,
                "The uploaded file contains no rows."
            ),
            {}
        )

    raw_df = raw_df.copy()

    raw_df.columns = [
        _norm_header(c)
        for c in raw_df.columns
    ]

    mapping, missing = _column_mapping(raw_df)

    if missing:
        return (
            pd.DataFrame(),
            ValidationReport(
                ok=False,
                message=(
                    "Required Google Forms questions are missing."
                ),
                row_count=len(raw_df),
                mapped_fields=len(mapping),
                missing_questions=missing,
            ),
            mapping,
        )

    canonical = pd.DataFrame(
        index=raw_df.index
    )

    # Timestamp remains supported if the uploaded file contains it.
    # It is optional and no warning is generated if it is missing
    # or cannot be parsed.
    timestamp_col = next(
        (
            c
            for c in raw_df.columns
            if _norm_header(c)
            .lower()
            .startswith("timestamp")
        ),
        None
    )

    if timestamp_col:
        canonical["timestamp"] = pd.to_datetime(
            raw_df[timestamp_col],
            errors="coerce"
        )
    else:
        canonical["timestamp"] = pd.NaT

    for q, field in QUESTION_TO_CANONICAL.items():

        src = mapping.get(field)

        if src is None:

            if field == "feedback":
                canonical[field] = ""

            continue

        canonical[field] = raw_df[src]

    for field in [
        "age_group",
        "gender",
        "programme",
        "visit_frequency",
        "mobile_data_frequency",
    ]:
        canonical[field] = _clean_text(
            canonical[field]
        )

    invalid_numeric: dict[str, int] = {}

    for field in NUMERIC_FIELDS:

        numeric = pd.to_numeric(
            canonical[field],
            errors="coerce"
        )

        invalid = (
            canonical[field].notna()
            & numeric.isna()
        )

        out_of_range = (
            numeric.notna()
            & ~numeric.between(1, 5)
        )

        invalid_count = int(
            (invalid | out_of_range).sum()
        )

        if invalid_count:
            invalid_numeric[field] = invalid_count

        canonical[field] = numeric.astype("Float64")

    for field in [
        "improvement_areas",
        "mobile_data_reasons",
    ]:
        canonical[field] = canonical[field].apply(
            _clean_multiselect
        )

    canonical["feedback"] = (
        _clean_text(canonical["feedback"])
        .fillna("")
    )

    canonical["response_id"] = [
        f"R-{i:03d}"
        for i in range(1, len(canonical) + 1)
    ]

    duplicate_rows = int(
        raw_df.duplicated().sum()
    )

    missing_values = {
        FRIENDLY_NAMES[field]: int(
            canonical[field].isna().sum()
        )
        for field in CANONICAL_FIELDS
        if (
            field in canonical.columns
            and int(canonical[field].isna().sum()) > 0
        )
    }

    warnings: list[str] = []

    if duplicate_rows:
        warnings.append(
            f"{duplicate_rows} exact duplicate row(s) "
            "detected; retained for transparency."
        )

    if invalid_numeric:
        warnings.append(
            "Some satisfaction responses are outside "
            "the 1–5 scale or non-numeric."
        )

    # Timestamp warning intentionally removed.
    # The dashboard will no longer display:
    # "Some timestamps could not be parsed; "
    # "the affected responses remain included."

    ok = not bool(invalid_numeric)

    message = (
        "Valid Survey Format"
        if ok
        else "Dataset contains invalid Likert values."
    )

    report = ValidationReport(
        ok=ok,
        message=message,
        row_count=len(canonical),
        mapped_fields=len(mapping),
        missing_questions=[],
        invalid_numeric=invalid_numeric,
        missing_value_counts=missing_values,
        duplicate_rows=duplicate_rows,
        warnings=warnings,
    )

    return canonical, report, mapping


def load_uploaded_contents(
    contents: str,
    filename: str
) -> tuple[
    pd.DataFrame,
    ValidationReport,
    dict[str, str]
]:

    raw = _read_dataframe(
        contents,
        filename
    )

    return prepare_dataframe(raw)


def dataframe_from_json(
    data: str | None
) -> pd.DataFrame:

    if not data:
        return pd.DataFrame()

    return pd.read_json(
        io.StringIO(data),
        orient="split"
    )


def dataframe_to_json(
    df: pd.DataFrame
) -> str:

    return df.to_json(
        orient="split",
        date_format="iso"
    )