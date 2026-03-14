# HomeSquare
### AI-Powered Real Estate Deal Analyzer

HomeSquare is an end-to-end AI system that evaluates real-estate listings and determines whether a property is a **deal**, **fair-priced**, or a **dud** based on comparable sales, machine-learned price models, and real-time scraped listing data.

This project combines **web scraping**, **data analysis**, and **machine learning** into a unified full-stack application with both a modern frontend and a robust backend.

---

## Features

### Real-Time Listing Analysis
- Scrapes live property data from **Zillow** and **Redfin**
- Extracts beds, baths, sqft, price, address, and listing URL
- Computes local comparable sales (comps) for the same ZIP code (Redfin)
- Uses recent sold listings to estimate median $/sqft

### Valuation Core (Baseline + ML)
- Baseline: blended median $/sqft from comps with light bed/bath adjustments
- ML: **CatBoost quantile regression** for median + prediction intervals
- Blends comps + ML median based on comp count
- Uses a tight +/-$10,000 band for Deal / Fair / Dud classification
- Confidence grows with comp count and distance outside the band

### Backend API (Flask)
- `/api/analyze_ai` endpoint processes listing URLs
- Merges scraped results + ML estimates
- Returns:
  - Estimated fair price
  - Label: `deal`, `fair`, `dud`
  - Confidence score
  - Explanation text
  - Raw model features

### Frontend (React + Vite + TypeScript)
- Clean UI for pasting URLs and viewing results
- Component-based design
- Smooth fetch to backend using `VITE_API_URL`
- Displays price estimate, % difference, comps, and reasoning
- Dark mode compatible

### Tech Stack
| Layer | Tech |
|-------|------|
| **Frontend** | React, TypeScript, Vite |
| **Backend** | Python, Flask, Pandas, NumPy |
| **Scraping** | Selenium, BeautifulSoup |
| **ML** | CatBoost, scikit-learn, joblib |
| **Storage** | SQLite, CSV datasets |
| **Deployment** | Render / Railway / EC2 |

---

## How It Works

### 1. User submits a listing URL
Frontend sends the URL to the backend via `/api/analyze_ai`.

### 2. Backend scrapes Zillow/Redfin
Extracts:
- Price
- Beds/Baths/Sqft
- ZIP code
- Hidden JSON state
- Similar homes for comp metrics

### 3. Build feature set
Backend computes:
- Median price per sqft
- IQR dispersion
- Median beds/baths/sqft in area
- Comps count
- Engineered numeric features (ratios, logs)

### 4. Machine Learning inference
CatBoost quantile models predict median price and intervals (P10/P50/P90).

### 5. Deal / Fair / Dud
Rules:
- Within $10k -> **fair**
- $10k above -> **dud**
- $10k below -> **deal**

### 6. Frontend displays full analysis
- Estimated fair price
- Confidence
- % difference
- Color-coded label
- Explanation text
- Comps preview
- ML interval (when available)

---

## Project Structure
```
HomeSquare/
|-- backend/
|   |-- app/
|   |   |-- routes/
|   |   |-- ai_core.py
|   |   |-- scraper.py
|   |   `-- ...
|   |-- database/        # SQLite DB lives here
|   |   `-- homesquare.db
|   `-- test_request.py
|
`-- frontend/
    |-- pages/
    |-- components/
    |-- index.html
    |-- index.tsx
    `-- App.tsx
```

---

## Local Development

### Backend
```bash
dcd backend
pip install -r requirements.txt
python run.py   # or flask run
```

### Frontend
```bash
dcd frontend
npm install
npm run dev
```

### Environment Variables
Frontend:
```
VITE_API_URL=http://localhost:5050
```

---

## Training Your Own Model

### Single model (all data or filtered)
```bash
source backend/.venv/bin/activate
python -m backend.app.ml.train \
  --data backend/data/realtor-data.zip.csv \
  --model-dir backend/app/models/price_model \
  --price-min 10000 \
  --price-max 5000000 \
  --sqft-min 300 \
  --sqft-max 10000
```

### Per-state models (recommended for accuracy)
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

The API automatically selects a state model if the listing state can be parsed.

---

## Example Output
```
Estimated fair price ~= $846,780
List price is -5.5% vs estimate -> FAIR
Confidence: 0.52
Comps Used: 1
Median $/sqft ~= $213
```

---

## Future Improvements
- Switch Selenium -> Playwright
- Add historical tracking + price alerts
- Add mapping UI for comps
- Use LightGBM for quantile intervals
- Deploy backend via Docker + Render

---

## Author
**Amanjeet Sahagal**

AI Engineering | Full-Stack Development | Real Estate Analytics
