from __future__ import annotations

import argparse
import json
import os
from typing import Dict, Tuple

import numpy as np
import pandas as pd
from catboost import CatBoostRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error

from .features import (
    FEATURE_COLS,
    CATEGORICAL_COLS,
    NUMERIC_COLS,
    TARGET_COL,
    DATE_COL,
    prepare_features,
)


def _load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    return df


def _clean_target(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df[TARGET_COL] = pd.to_numeric(df[TARGET_COL], errors="coerce")
    df["house_size"] = pd.to_numeric(df.get("house_size"), errors="coerce")
    df = df.dropna(subset=[TARGET_COL, "house_size"])
    df = df[(df[TARGET_COL] > 0) & (df["house_size"] > 0)]
    return df


def _apply_filters(
    df: pd.DataFrame,
    states: list[str] | None,
    price_min: float | None,
    price_max: float | None,
    sqft_min: float | None,
    sqft_max: float | None,
) -> pd.DataFrame:
    df = df.copy()
    if states:
        df["state"] = df["state"].astype("string")
        upper = {s.upper() for s in states}
        df = df[df["state"].str.upper().isin(upper)]
    if price_min is not None:
        df = df[df[TARGET_COL] >= price_min]
    if price_max is not None:
        df = df[df[TARGET_COL] <= price_max]
    if sqft_min is not None:
        df = df[df["house_size"] >= sqft_min]
    if sqft_max is not None:
        df = df[df["house_size"] <= sqft_max]
    return df


def _build_zip_maps(df: pd.DataFrame) -> Dict[str, Dict[str, str]]:
    df = df.copy()
    df["zip_code"] = df["zip_code"].astype("string")
    df["city"] = df["city"].astype("string")
    df["state"] = df["state"].astype("string")

    def _mode(series: pd.Series) -> str:
        series = series.dropna()
        if series.empty:
            return "unknown"
        return series.value_counts().idxmax()

    zip_to_state = df.groupby("zip_code")["state"].apply(_mode).to_dict()
    zip_to_city = df.groupby("zip_code")["city"].apply(_mode).to_dict()
    return {"zip_to_state": zip_to_state, "zip_to_city": zip_to_city}


def _split_data(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    if DATE_COL in df.columns:
        parsed = pd.to_datetime(df[DATE_COL], errors="coerce")
        df = df.assign(_parsed_date=parsed)
        if df["_parsed_date"].notna().sum() > 5000:
            df = df.sort_values("_parsed_date")
            split_idx = int(len(df) * 0.8)
            train_df = df.iloc[:split_idx]
            test_df = df.iloc[split_idx:]
            return train_df.drop(columns=["_parsed_date"]), test_df.drop(columns=["_parsed_date"])
    train_df, test_df = train_test_split(df, test_size=0.2, random_state=42)
    return train_df, test_df


def _fit_model(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    cat_features: list[int],
    alpha: float,
) -> CatBoostRegressor:
    model = CatBoostRegressor(
        loss_function=f"Quantile:alpha={alpha}",
        eval_metric="MAE",
        depth=8,
        learning_rate=0.1,
        iterations=800,
        random_seed=42,
        verbose=False,
    )
    model.fit(
        X_train,
        y_train,
        eval_set=(X_val, y_val),
        cat_features=cat_features,
        use_best_model=True,
    )
    return model


def _train_single(df: pd.DataFrame, model_dir: str) -> None:
    train_df, test_df = _split_data(df)

    train_prep = prepare_features(train_df, target_col=TARGET_COL)
    test_prep = prepare_features(
        test_df,
        target_col=TARGET_COL,
        numeric_medians=train_prep.numeric_medians,
        ref_date=train_prep.ref_date,
    )

    X_train, y_train = train_prep.X, train_prep.y
    X_test, y_test = test_prep.X, test_prep.y

    cat_features = [FEATURE_COLS.index(c) for c in CATEGORICAL_COLS]

    models = {
        "q10": _fit_model(X_train, y_train, X_test, y_test, cat_features, 0.1),
        "q50": _fit_model(X_train, y_train, X_test, y_test, cat_features, 0.5),
        "q90": _fit_model(X_train, y_train, X_test, y_test, cat_features, 0.9),
    }

    preds = models["q50"].predict(X_test)
    mae = float(mean_absolute_error(y_test, preds))
    mape = float(np.mean(np.abs((y_test - preds) / y_test)))
    q10 = models["q10"].predict(X_test)
    q90 = models["q90"].predict(X_test)
    coverage = float(np.mean((y_test >= q10) & (y_test <= q90)))
    interval_width = float(np.mean(q90 - q10))

    os.makedirs(model_dir, exist_ok=True)

    for name, model in models.items():
        model_path = os.path.join(model_dir, f"catboost_{name}.cbm")
        model.save_model(model_path)

    zip_maps = _build_zip_maps(train_df)
    metadata = {
        "target": TARGET_COL,
        "feature_cols": FEATURE_COLS,
        "categorical_cols": CATEGORICAL_COLS,
        "numeric_cols": NUMERIC_COLS,
        "numeric_medians": train_prep.numeric_medians,
        "ref_date": train_prep.ref_date,
        "zip_to_state": zip_maps["zip_to_state"],
        "zip_to_city": zip_maps["zip_to_city"],
        "train_rows": int(len(train_df)),
        "test_rows": int(len(test_df)),
        "metrics": {
            "mae": mae,
            "mape": mape,
            "interval_coverage_80": coverage,
            "interval_width_mean": interval_width,
        },
    }

    with open(os.path.join(model_dir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print("Saved models to", model_dir)
    print("MAE:", mae)
    print("MAPE:", mape)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train CatBoost price model with quantile intervals.")
    parser.add_argument("--data", required=True, help="Path to CSV dataset")
    parser.add_argument("--model-dir", default="backend/app/models/price_model", help="Output model directory")
    parser.add_argument("--max-rows", type=int, default=0, help="Optional row cap for faster training")
    parser.add_argument("--state", default="", help="Filter to a single state (e.g., CA, TX)")
    parser.add_argument("--states", default="", help="Comma-separated list of states (e.g., CA,TX,FL)")
    parser.add_argument("--price-min", type=float, default=None, help="Minimum price filter")
    parser.add_argument("--price-max", type=float, default=None, help="Maximum price filter")
    parser.add_argument("--sqft-min", type=float, default=None, help="Minimum house_size filter")
    parser.add_argument("--sqft-max", type=float, default=None, help="Maximum house_size filter")
    parser.add_argument("--by-state", action="store_true", help="Train one model per state")
    args = parser.parse_args()

    df = _load_data(args.data)
    df = _clean_target(df)
    states = [s.strip() for s in args.states.split(",") if s.strip()] if args.states else []
    if args.state.strip():
        states.append(args.state.strip())

    df = _apply_filters(
        df,
        states=states or None,
        price_min=args.price_min,
        price_max=args.price_max,
        sqft_min=args.sqft_min,
        sqft_max=args.sqft_max,
    )

    if args.max_rows and len(df) > args.max_rows:
        df = df.sample(n=args.max_rows, random_state=42)

    if args.by_state:
        df["state"] = df["state"].astype("string")
        for state_name, group in df.groupby(df["state"].str.upper()):
            if not state_name or state_name == "NAN":
                continue
            state_dir = os.path.join(args.model_dir, state_name)
            print(f"Training state model: {state_name} ({len(group)} rows)")
            _train_single(group, state_dir)
    else:
        _train_single(df, args.model_dir)


if __name__ == "__main__":
    main()
