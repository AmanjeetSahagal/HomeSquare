# ML Pipeline

This module trains a CatBoost price model with prediction intervals (10/50/90 quantiles) using the Realtor dataset.

## Dataset
Expected columns (from `realtor-data.zip.csv`):

- `price` (target)
- `bed`, `bath`, `house_size`, `acre_lot`
- `street`, `city`, `state`, `zip_code`
- `status`, `brokered_by`
- `prev_sold_date`

## Train

```bash
source backend/.venv/bin/activate
python -m backend.app.ml.train \
  --data backend/data/realtor-data.zip.csv \
  --model-dir backend/app/models/price_model
```

Optional: speed up training

```bash
python -m backend.app.ml.train --data backend/data/realtor-data.zip.csv --model-dir backend/app/models/price_model --max-rows 200000
```

## Train Per-State Models

```bash
python -m backend.app.ml.train \
  --data backend/data/realtor-data.zip.csv \
  --model-dir backend/app/models/price_model \
  --by-state \
  --price-min 10000 \
  --price-max 5000000 \
  --sqft-min 300 \
  --sqft-max 10000
```

This will write models to `backend/app/models/price_model/<STATE_NAME>/` (e.g., `NEW YORK`).
The API will automatically select the state model if the listing state can be parsed.

## Inference
Models are loaded automatically by `backend/app/ml/inference.py` if `backend/app/models/price_model/metadata.json` exists.

The API will return:
- `ML Estimated Price`
- `ML Interval Low`
- `ML Interval High`

If no model exists, the API uses the comps baseline only.
