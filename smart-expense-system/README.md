# Smart Expense Intelligence System

AI-powered Nigerian bank transaction classifier and analytics dashboard.
Built with FastAPI + Next.js 14 + BERT Prototypical Networks.

---

## Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.9 or higher |
| Node.js | 18 or higher |
| npm | 9 or higher |

---

## Step 1 — Place your ML model

Copy your trained model into the backend's model directory:

```
smart-expense-system/
└── backend/
    └── ml_model/
        └── expense_model.pkl   ← put it here
```

The pkl file must contain a Python dict: `{ "category_name": numpy_array }`.
Keys must be any of: `food`, `transport`, `entertainment`, `bills`, `health`,
`education`, `shopping`, `other`.

> If the file is missing the system auto-generates default prototypes from
> seed sentences and the app still works — corrections will refine it.

---

## Step 2 — Backend setup

Open **Terminal 1** and run:

```bash
cd smart-expense-system/backend

# Create and activate virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# Install dependencies (first run downloads ~500 MB for the transformer model)
pip install -r requirements.txt

# Start the API server
uvicorn main:app --reload
```

The API will be live at **http://localhost:8000**
Interactive docs: **http://localhost:8000/docs**

---

## Step 3 — Frontend setup

Open **Terminal 2** and run:

```bash
cd smart-expense-system/frontend

npm install

npm run dev
```

The app will be live at **http://localhost:3000**

---

## Step 4 — Test with sample data

1. Open http://localhost:3000
2. Click the upload area and select:
   `backend/ml_model/sample_transactions.csv`
3. The AI classifies all 50 rows and redirects you to the Dashboard
4. Navigate to Transactions to view predictions and make corrections

---

## API Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| POST | `/upload` | Upload CSV / Excel file |
| POST | `/categorize` | Classify a single description |
| POST | `/correct` | Correct a transaction category |
| GET | `/analytics` | Spending analytics (pass `?session_id=`) |
| GET | `/transactions` | List transactions (pass `?session_id=`) |
| GET | `/docs` | Swagger UI |

---

## Project Structure

```
smart-expense-system/
├── backend/
│   ├── main.py                      FastAPI app + lifespan startup
│   ├── routes/
│   │   ├── upload.py                CSV/Excel ingestion + batch classify
│   │   ├── categorize.py            Single-description classify
│   │   ├── correct.py               Label correction + prototype update
│   │   ├── analytics.py             Spending analytics
│   │   └── transactions.py          Transaction list endpoint
│   ├── services/
│   │   ├── classifier.py            BERT + prototypical network inference
│   │   └── analytics_service.py     Aggregation logic
│   ├── models/
│   │   └── database.py              SQLAlchemy / SQLite schema
│   ├── ml_model/
│   │   ├── expense_model.pkl        ← YOUR MODEL GOES HERE
│   │   ├── README.txt
│   │   └── sample_transactions.csv
│   └── requirements.txt
│
└── frontend/
    ├── app/
    │   ├── page.tsx                 Landing / upload page
    │   ├── dashboard/page.tsx       Analytics dashboard
    │   └── transactions/page.tsx    Transaction table + corrections
    ├── components/
    │   ├── FileUpload.tsx
    │   ├── TransactionTable.tsx
    │   ├── CategoryChart.tsx        Recharts PieChart
    │   ├── MonthlyChart.tsx         Recharts BarChart
    │   └── Navbar.tsx
    └── lib/
        └── api.ts                   All fetch calls to FastAPI
```
