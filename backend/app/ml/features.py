from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime

import numpy as np
import pandas as pd

TARGET_COL = "price"
DATE_COL = "prev_sold_date"

CATEGORICAL_COLS = [
    "brokered_by",
    "status",
    "street",
    "city",
    "state",
    "zip_code",
]

NUMERIC_COLS = [
    "bed",
    "bath",
    "acre_lot",
    "house_size",
]

ENGINEERED_NUMERIC_COLS = [
    "lot_sqft",
    "house_size_log",
    "acre_lot_log",
    "bed_bath_ratio",
    "beds_per_1000_sqft",
    "baths_per_1000_sqft",
]

DATE_FEATURES = [
    "prev_sold_year",
    "prev_sold_month",
    "prev_sold_days_ago",
]

FEATURE_COLS = NUMERIC_COLS + ENGINEERED_NUMERIC_COLS + DATE_FEATURES + CATEGORICAL_COLS


@dataclass
class FeaturePrepResult:
    X: pd.DataFrame
    y: Optional[pd.Series]
    numeric_medians: Dict[str, float]
    ref_date: str


def _ensure_columns(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    for col in cols:
        if col not in df.columns:
            df[col] = None
    return df


def _parse_dates(df: pd.DataFrame) -> pd.Series:
    return pd.to_datetime(df[DATE_COL], errors="coerce", utc=False)


def prepare_features(
    df: pd.DataFrame,
    target_col: str = TARGET_COL,
    numeric_medians: Optional[Dict[str, float]] = None,
    ref_date: Optional[str] = None,
) -> FeaturePrepResult:
    df = df.copy()

    df = _ensure_columns(df, FEATURE_COLS + [target_col, DATE_COL])

    # Parse date features
    parsed_dates = _parse_dates(df)
    if ref_date is None:
        max_date = parsed_dates.dropna().max()
        ref_dt = max_date.to_pydatetime() if pd.notna(max_date) else datetime.utcnow()
    else:
        ref_dt = datetime.fromisoformat(ref_date)

    df["prev_sold_year"] = parsed_dates.dt.year
    df["prev_sold_month"] = parsed_dates.dt.month
    df["prev_sold_days_ago"] = (ref_dt - parsed_dates).dt.days

    # Categorical cleanup
    for col in CATEGORICAL_COLS:
        df[col] = df[col].astype("string").fillna("unknown")

    # Numeric cleanup
    for col in NUMERIC_COLS + DATE_FEATURES:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Engineered numeric features
    df["lot_sqft"] = df["acre_lot"] * 43560
    df["house_size_log"] = np.log(df["house_size"].clip(lower=1))
    df["acre_lot_log"] = np.log(df["acre_lot"].clip(lower=1e-6))
    df["bed_bath_ratio"] = df["bed"] / df["bath"].replace({0: pd.NA})
    df["beds_per_1000_sqft"] = df["bed"] / (df["house_size"] / 1000).replace({0: pd.NA})
    df["baths_per_1000_sqft"] = df["bath"] / (df["house_size"] / 1000).replace({0: pd.NA})
    df[ENGINEERED_NUMERIC_COLS] = df[ENGINEERED_NUMERIC_COLS].replace([np.inf, -np.inf], np.nan)

    if numeric_medians is None:
        numeric_medians = {}
        for col in NUMERIC_COLS + ENGINEERED_NUMERIC_COLS + DATE_FEATURES:
            med = df[col].median()
            numeric_medians[col] = float(med) if pd.notna(med) else 0.0

    for col, med in numeric_medians.items():
        if col in df.columns:
            df[col] = df[col].fillna(med)

    y = None
    if target_col in df.columns:
        y = pd.to_numeric(df[target_col], errors="coerce")

    X = df[FEATURE_COLS]

    return FeaturePrepResult(
        X=X,
        y=y,
        numeric_medians=numeric_medians,
        ref_date=ref_dt.isoformat(),
    )
