from flask import Blueprint, request, jsonify
import re
import pandas as pd

from ..ai_core import (
    Listing,
    build_features,
    estimate_price_baseline,
    label_deal,
    explanation_text,
)
from ..scraper import scrape_listing, get_average_price_redfin, get_comps_redfin

ai = Blueprint("ai", __name__)


def _to_float(x):
    """Safely convert strings like '$500,000' to float."""
    try:
        if x is None:
            return None
        if isinstance(x, (int, float)):
            return float(x)
        s = str(x).replace("$", "").replace(",", "").strip()
        return float(s) if s else None
    except Exception:
        return None


def _zip_from_url(url: str):
    """Extract ZIP code from URL (Redfin/Zillow usually include it)."""
    m = re.search(r"(\d{5})(?:[-/]|$)", url or "")
    return m.group(1) if m else None


@ai.post("/analyze_ai")
def analyze_ai():
    """
    POST /analyze_ai
    {
        "url": "<Zillow or Redfin URL>"
    }
    """

    data = request.get_json(silent=True) or {}
    url = data.get("url")

    if not url:
        return jsonify({"status": "error", "error": "Missing 'url'"}), 400

    # Step 1️ — Scrape the main listing
    try:
        listing_data = scrape_listing(url)
        list_price = _to_float(listing_data.get("Price"))
        beds = _to_float(listing_data.get("Beds"))
        baths = _to_float(listing_data.get("Baths"))
        sqft = _to_float(listing_data.get("Square Footage"))
        zip_code = _zip_from_url(url)

        comps_df = None

        # Prefer actual comps extracted from Redfin page state
        raw_comps = listing_data.get("Comps") if isinstance(listing_data, dict) else None
        if isinstance(raw_comps, list) and len(raw_comps) >= 3:
            comps_df = pd.DataFrame(raw_comps)
        else:
            try:
                comps = get_comps_redfin(
                    zip_code=zip_code,
                    beds=int(beds or 3),
                    baths=int(baths or 2),
                    sqft=int(sqft or 1500),
                    tol=0.2,
                    limit=25
                )
            except Exception as e:
                return jsonify({"status": "error", "error": f"Failed to get Redfin comps: {e}"}), 500

            if comps:
                comps_df = pd.DataFrame(comps)
            else:
                avg_price = get_average_price_redfin(
                    zip_code=zip_code,
                    beds=int(beds or 3),
                    baths=int(baths or 2),
                    sqft=int(sqft or 1500),
                    tol=0.2
                )

                if avg_price is None:
                    return jsonify({"status": "error", "error": "No comparable homes found (Redfin search returned none)."}), 404

                # Construct a small synthetic comps DataFrame using that average
                comps_df = pd.DataFrame([{
                    "price": avg_price,
                    "sqft": sqft,
                    "beds": beds,
                    "baths": baths
                }])

        # If comps exist but missing sqft, fall back to a synthetic average row
        if comps_df is not None and not comps_df.empty and "sqft" in comps_df.columns:
            comps_df["sqft"] = pd.to_numeric(comps_df["sqft"], errors="coerce")
        if comps_df is not None and not comps_df.empty:
            if "price" in comps_df.columns:
                prices = pd.to_numeric(comps_df["price"], errors="coerce").dropna()
            else:
                prices = pd.Series([], dtype=float)
            if comps_df.dropna(subset=["price", "sqft"]).empty and not prices.empty:
                avg_price = float(prices.mean())
                comps_df = pd.DataFrame([{
                    "price": avg_price,
                    "sqft": sqft,
                    "beds": beds,
                    "baths": baths
                }])

        
    except Exception as e:
        return jsonify({"status": "error", "error": f"Scrape failed: {e}"}), 500

    # Step 2️ — Extract key info
    list_price = _to_float(listing_data.get("Price"))
    beds = _to_float(listing_data.get("Beds"))
    baths = _to_float(listing_data.get("Baths"))
    sqft = _to_float(listing_data.get("Square Footage"))
    zip_code = _zip_from_url(url)

    # Build a listing object for analysis
    listing = Listing(
        price=list_price,
        beds=beds,
        baths=baths,
        sqft=sqft,
        zip_code=zip_code,
    )

    # Step 3 — Compute AI features + estimated value
    if comps_df is None or comps_df.empty:
        return jsonify({"status": "error", "error": "No valid comps available to estimate price."}), 404
    feats = build_features(listing, comps_df)
    if feats.get("n_comps", 0) == 0:
        return jsonify({"status": "error", "error": "No valid comps available to estimate price."}), 404
    est_price = estimate_price_baseline(listing, feats)
    label, confidence, pct_diff = label_deal(
        list_price, est_price, feats["n_comps"]
    )
    explanation = explanation_text(listing, est_price, label, pct_diff, feats)

    # Step 4 — Build small preview of comps (safe columns)
    preview_cols = [c for c in ["price", "beds", "baths", "sqft", "address", "detail_url"] if c in comps_df.columns]
    sample_comps = comps_df.head(8)[preview_cols].to_dict(orient="records")

    # If you used the ZIP-average fallback and only have one synthetic row,
    # you can add a helpful note for the frontend:
    if len(sample_comps) == 1 and ("address" not in preview_cols or "detail_url" not in preview_cols):
        sample_comps[0]["note"] = "Aggregate from ZIP comps (no individual addresses)"


    # Step 5 — Return structured JSON

    pct_out = None if pd.isna(pct_diff) else round(float(pct_diff), 4)
    est_out = None if pd.isna(est_price) else round(float(est_price), 2)
    if est_out is None:
        label, confidence = "unknown", 0.2

    return jsonify({
        "status": "success",
        "data": {
            "Address": listing_data.get("Address"),
            "Price": list_price,
            "Beds": beds,
            "Baths": baths,
            "Square Footage": sqft,
            "Estimated Price": est_out,
            "Label": label,
            "Confidence": round(float(confidence), 3),
            "Percent Difference": pct_out,
            "Explanation": explanation,
            "CompsUsed": int(len(comps_df)),
            "CompsPreview": sample_comps
        }
    }), 200
