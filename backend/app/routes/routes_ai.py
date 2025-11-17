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
from ..scraper import scrape_listing, get_average_price_redfin

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

        try:
            avg_price = get_average_price_redfin(
                zip_code=zip_code,
                beds=int(beds or 3),
                baths=int(baths or 2),
                sqft=int(sqft or 1500),
                tol=0.2
            )
        except Exception as e:
            return jsonify({"status": "error", "error": f"Failed to get Redfin comps: {e}"}), 500

        if avg_price is None:
            return jsonify({"status": "error", "error": "No comparable homes found (Redfin search returned none)."}), 404

        # Construct a small synthetic comps DataFrame using that average
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
    feats = build_features(listing, comps_df)
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
    preview_cols = [c for c in ["price","beds","baths","sqft","address","detail_url"] if c in comps_df.columns]
    sample_comps = comps_df.head(8)[preview_cols].to_dict(orient="records")

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
