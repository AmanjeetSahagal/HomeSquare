from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Dict, Optional

import pandas as pd
from catboost import CatBoostRegressor

from .features import FEATURE_COLS, prepare_features


class PriceModel:
    def __init__(self, model_dir: str):
        meta_path = os.path.join(model_dir, "metadata.json")
        if not os.path.exists(meta_path):
            raise FileNotFoundError(f"metadata.json not found in {model_dir}")

        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        self.model_dir = model_dir
        self.target = meta.get("target", "price")
        self.feature_cols = meta.get("feature_cols", FEATURE_COLS)
        self.numeric_medians = meta.get("numeric_medians", {})
        self.ref_date = meta.get("ref_date")
        self.zip_to_state = meta.get("zip_to_state", {})
        self.zip_to_city = meta.get("zip_to_city", {})

        self.model_q10 = self._load_model("catboost_q10.cbm")
        self.model_q50 = self._load_model("catboost_q50.cbm")
        self.model_q90 = self._load_model("catboost_q90.cbm")

    def _load_model(self, filename: str) -> CatBoostRegressor:
        path = os.path.join(self.model_dir, filename)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Model file not found: {path}")
        model = CatBoostRegressor()
        model.load_model(path)
        return model

    def predict(self, listing: Dict[str, object]) -> Optional[Dict[str, float]]:
        listing = dict(listing)
        zip_code = listing.get("zip_code")
        if zip_code is not None:
            zip_key = str(zip_code)
            if not listing.get("state"):
                listing["state"] = self.zip_to_state.get(zip_key)
            if not listing.get("city"):
                listing["city"] = self.zip_to_city.get(zip_key)

        df = pd.DataFrame([listing])
        prep = prepare_features(
            df,
            target_col=self.target,
            numeric_medians=self.numeric_medians,
            ref_date=self.ref_date,
        )
        X = prep.X
        for col in self.feature_cols:
            if col not in X.columns:
                X[col] = None
        X = X[self.feature_cols]

        p10 = float(self.model_q10.predict(X)[0])
        p50 = float(self.model_q50.predict(X)[0])
        p90 = float(self.model_q90.predict(X)[0])
        return {"p10": p10, "p50": p50, "p90": p90}


@lru_cache(maxsize=1)
def load_price_model(model_dir: Optional[str] = None) -> Optional[PriceModel]:
    if model_dir is None:
        model_dir = os.path.join(os.path.dirname(__file__), "..", "models", "price_model")
        model_dir = os.path.normpath(model_dir)
    meta_path = os.path.join(model_dir, "metadata.json")
    if not os.path.exists(meta_path):
        return None
    return PriceModel(model_dir)


def load_price_model_for_state(state: Optional[str] = None) -> Optional[PriceModel]:
    base_dir = os.path.join(os.path.dirname(__file__), "..", "models", "price_model")
    base_dir = os.path.normpath(base_dir)
    if state:
        state_dir = os.path.join(base_dir, state.upper())
        if os.path.exists(os.path.join(state_dir, "metadata.json")):
            return PriceModel(state_dir)
    return load_price_model(base_dir)
