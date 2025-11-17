

# 🏡 HomeSquare
### AI-Powered Real Estate Deal Analyzer

HomeSquare is an end-to-end AI system that evaluates real-estate listings and determines whether a property is a **deal**, **fair-priced**, or a **dud** based on comparable sales, machine-learned price models, and real-time scraped listing data.

This project combines **web scraping**, **data analysis**, and **machine learning** into a unified full-stack application with both a modern frontend and a robust backend.

---

## 🚀 Features

### 🔍 Real-Time Listing Analysis
- Scrapes live property data from **Zillow** and **Redfin**
- Extracts beds, baths, sqft, price, HOA, location, and structured hidden state
- Computes local comparable sales (comps) for the same ZIP code
- Uses ≥1 year of sold listings to estimate median $/sqft

### 🤖 Machine Learning Core
- Trains a supervised ML model using:
  - Your scraped comps
  - External Kaggle datasets
- Scikit-learn pipeline with:
  - Numeric + categorical encoding
  - Feature scaling
  - Gradient-boosted regression
- Optional prediction intervals and confidence estimates
- Blends model output with comp-based medians for stability
- Uses a **tight ±$10,000 band** for Deal / Fair / Dud classification

### ⚙️ Backend API (Flask)
- `/api/analyze_ai` endpoint processes listing URLs
- Merges scraped results + ML estimates
- Returns:
  - Estimated fair price
  - Label: `deal`, `fair`, `dud`
  - Confidence score
  - Explanation text
  - Raw model features

### 💻 Frontend (React + Vite + TypeScript)
- Clean UI for pasting URLs and viewing results
- Component-based design
- Smooth fetch to backend using `VITE_API_URL`
- Displays price estimate, % difference, comps, and reasoning
- Dark mode compatible

### 🗃 Tech Stack
| Layer | Tech |
|-------|------|
| **Frontend** | React, TypeScript, Vite |
| **Backend** | Python, Flask, Pandas, NumPy |
| **Scraping** | Selenium, BeautifulSoup |
| **ML** | scikit-learn, joblib, Pydantic |
| **Storage** | CSV datasets, cached comp results |
| **Deployment** | Render / Railway / EC2 |

---

## 🧠 How It Works

### 1️⃣ User submits a listing URL
Frontend sends the URL to the backend via `/api/analyze_ai`.

### 2️⃣ Backend scrapes Zillow/Redfin
Extracts:
- Price
- Beds/Baths/Sqft
- ZIP code
- Hidden JSON state
- Similar homes for comp metrics

### 3️⃣ Build feature set
Backend computes:
- Median price per sqft
- IQR dispersion
- Median beds/baths/sqft in area
- Comps count
- External Kaggle priors (ZIP-level $/sqft)
- Blended model features

### 4️⃣ Machine Learning inference
Price model predicts expected fair price.
Optional: quantile models produce prediction intervals.

### 5️⃣ Deal / Fair / Dud
Rules:
- Within $10k → **fair**
- $10k above → **dud**
- $10k below → **deal**

### 6️⃣ Frontend displays full analysis
- Estimated fair price
- Confidence
- % difference
- Color-coded label
- Explanation text
- Comps preview
- Raw model features

---

## 📂 Project Structure
```
HomeSquare/
├── backend/
│   ├── app/
│   │   ├── routes/
│   │   ├── ai_core.py
│   │   ├── ...
│   ├── ml/
│   │   ├── schema.py
│   │   ├── features.py
│   │   ├── train.py
│   │   ├── inference.py
│   ├── models/
│   ├── data/
│   └── test_request.py
│
└── frontend/
    ├── src/
    │   ├── pages/
    │   ├── components/
    │   └── ...
    ├── public/
    ├── index.html
    └── vite.config.ts
```

---

## 🛠 Local Development

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

Backend:
```
CHROME_DRIVER_PATH=...
DEBUG_SELENIUM=1
```

---

## 📈 Training Your Own Model
```bash
cd backend/app/ml
python train.py --kaggle data/kaggle.csv --scraped data/scraped.csv
```

Output saved to:
```
backend/app/models/price_pipe.joblib
```

---

## 🧪 Example Output
```
Estimated fair price ≈ $846,780
List price is -5.5% vs estimate → FAIR
Confidence: 0.52
Comps Used: 1
Median $/sqft ≈ $213
```

---

## 🧭 Future Improvements
- Switch Selenium → Playwright
- Add historical tracking + price alerts
- Add mapping UI for comps
- Use LightGBM for quantile intervals
- Deploy backend via Docker + Render

---

## 🙌 Author
**Amanjeet Sahagal**

AI Engineering • Full-Stack Development • Real Estate Analytics