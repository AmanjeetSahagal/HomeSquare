from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import math
import pandas as pd
import numpy as np
from statistics import median

def load_external_stats(csv_path: str) -> Dict[str, Any]:
    """Load external dataset (e.g., Kaggle). Expects columns: price, sqft, zip_code.
    Returns a dict with median $/sqft per ZIP for fast lookup.
    """
    df = pd.read_csv(csv_path)
    for col in ["price", "sqft"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    # normalize zip col name variants
    if "zip" in df.columns and "zip_code" not in df.columns:
        df.rename(columns={"zip": "zip_code"}, inplace=True)
    df = df.dropna(subset=["price", "sqft", "zip_code"]).copy()
    df["ppsqft"] = df["price"]/df["sqft"]
    med_per_zip = df.groupby("zip_code")["ppsqft"].median().to_dict()
    return {"zip_ppsqft": {str(k): float(v) for k, v in med_per_zip.items()}}

# ---------- Data Structures ----------
@dataclass
class Listing:
    price: Optional[float]
    beds: Optional[float]
    baths: Optional[float]
    sqft: Optional[float]
    zip_code: Optional[str]

@dataclass
class AnalysisResult:
    est_price: float
    label: str            # "deal" | "fair" | "dud"
    pct_diff: float       # (list_price - est_price)/est_price
    confidence: float     # 0 to 1
    explanation: str
    features: Dict[str, Any]

# ---------- Feature Builder ----------
def build_features(listing: Listing, comps_df: pd.DataFrame, external_stats: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    # Normalize comp columns
    for col in ["price", "beds", "baths", "sqft"]:
        if col in comps_df.columns:
            comps_df[col] = pd.to_numeric(comps_df[col], errors="coerce")
    comps_df = comps_df.dropna(subset=["price", "sqft"])

    avg_ppsqft = float(np.median(comps_df["price"] / comps_df["sqft"]))
    ppsqft_iqr = float(np.subtract(*np.percentile(comps_df["price"]/comps_df["sqft"], [75, 25])))

    # Optional: enrich with external (e.g., Kaggle) stats
    avg_ppsqft_external = None
    if external_stats and listing.zip_code:
        # expect external_stats to contain a mapping: { 'zip_ppsqft': { '23059': 215.0, ... } }
        zip_map = external_stats.get('zip_ppsqft') or {}
        avg_ppsqft_external = zip_map.get(str(listing.zip_code))

    # Blend local comps and external priors (favor local comps when available)
    if avg_ppsqft_external and not math.isnan(avg_ppsqft_external):
        blended_ppsqft = 0.6 * avg_ppsqft + 0.4 * float(avg_ppsqft_external)
    else:
        blended_ppsqft = avg_ppsqft

    beds_med = float(np.median(comps_df["beds"].dropna())) if "beds" in comps_df else np.nan
    baths_med = float(np.median(comps_df["baths"].dropna())) if "baths" in comps_df else np.nan
    sqft_med = float(np.median(comps_df["sqft"].dropna()))
    n_comps = int(len(comps_df))

    return {
        "avg_ppsqft": avg_ppsqft,
        "ppsqft_iqr": ppsqft_iqr,
        "beds_med": beds_med,
        "baths_med": baths_med,
        "sqft_med": sqft_med,
        "n_comps": n_comps,
        "avg_ppsqft_external": avg_ppsqft_external,
        "blended_ppsqft": blended_ppsqft
    }

# ---------- Price Estimator (baseline robust median) ----------
def estimate_price_baseline(listing: Listing, feats: Dict[str, Any]) -> float:
    ppsqft = feats.get("blended_ppsqft", feats.get("avg_ppsqft"))
    if not listing.sqft or not ppsqft or (isinstance(ppsqft, float) and math.isnan(ppsqft)):
        return float("nan")
    # Simple hedonic: price ≈ blended median $/sqft * subject sqft
    est = float(ppsqft) * float(listing.sqft)

    # Small adjustments for bedroom/bath deltas (very rough priors)
    bed_adj = 0.03  # ±3% per bedroom difference
    bath_adj = 0.02 # ±2% per bathroom difference
    if listing.beds and not math.isnan(feats.get("beds_med", float("nan"))):
        est *= (1 + bed_adj * ((listing.beds or 0) - (feats["beds_med"] or 0)))
    if listing.baths and not math.isnan(feats.get("baths_med", float("nan"))):
        est *= (1 + bath_adj * ((listing.baths or 0) - (feats["baths_med"] or 0)))

    return float(max(est, 0.0))

# ---------- Labeling ----------
def label_deal(list_price: Optional[float], est_price: float, n_comps: int) -> (str, float, float):
    if not list_price or not est_price or est_price <= 0:
        return "unknown", 0.2, float("nan")

    abs_diff = float(list_price) - float(est_price)
    pct_diff = abs_diff / float(est_price)

    # Tighter rating: FAIR within ±$10,000 absolute band
    band_abs = 10000.0
    if abs_diff <= -band_abs:
        label = "deal"
    elif abs_diff >= band_abs:
        label = "dud"
    else:
        label = "fair"

    # Confidence grows with comp count and distance outside the band
    margin = max(0.0, abs(abs_diff) - band_abs)
    conf = min(0.95, 0.5 + 0.02 * max(0, n_comps) + (margin / (band_abs * 2.0)))
    return label, conf, pct_diff

# ---------- Explanation (templated; LLM optional later) ----------
def explanation_text(listing: Listing, est_price: float, label: str, pct_diff: float, feats: Dict[str, Any]) -> str:
    pct = round(pct_diff * 100, 1) if pct_diff == pct_diff else "N/A"
    parts = [
        f"Estimated fair price ≈ ${est_price:,.0f} using median $/sqft × subject sqft",
    ]
    if feats.get('avg_ppsqft_external'):
        parts.append(
            f"(blended local comps + external prior; median $/sqft ≈ ${feats['blended_ppsqft']:,.0f})."
        )
    else:
        parts.append(
            f"(median $/sqft ≈ ${feats['avg_ppsqft']:,.0f} from {feats['n_comps']} comps)."
        )
    if isinstance(pct, (int, float)):
        parts.append(f"List price is {pct}% vs estimate → **{label.upper()}**.")
    # Add quick feature context
    if feats.get("ppsqft_iqr"):
        parts.append(f"Dispersion (IQR) in $/sqft ≈ ${feats['ppsqft_iqr']:,.0f} (pricing spread indicator).")
    parts.append("Fair uses a ±$10,000 band around the estimate.")
    return " ".join(parts)