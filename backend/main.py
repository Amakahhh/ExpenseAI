from fastapi import FastAPI, UploadFile, File
import pandas as pd
import numpy as np
import traceback

from backend.services.classifier import classify_transaction
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# HOME
# -----------------------------
@app.get("/")
def home():
    return {"message": "Expense Intelligence System Running"}


# -----------------------------
# UPLOAD ENDPOINT
# -----------------------------
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):

    try:
        filename = file.filename.lower()
        print(f"File received: {filename}")

        # -----------------------------
        # READ FILE (Without assuming first row is header)
        # -----------------------------
        if filename.endswith(".csv"):
            df = pd.read_csv(file.file, header=None)

        elif filename.endswith(".xlsx") or filename.endswith(".xls"):
            df = pd.read_excel(file.file, header=None)

        elif filename.endswith(".pdf"):
            return {"error": "PDF parsing not enabled in demo mode"}

        else:
            return {"error": "Only CSV, XLS, XLSX supported"}

        # -----------------------------
        # FIND THE TRUE HEADER ROW
        # -----------------------------
        possible_header_keywords = ["description", "narration", "name", "details", "transaction", "amount", "date", "balance"]
        header_idx = 0
        
        # Scan the first 20 rows to find header
        for idx in range(min(20, len(df))):
            row_vals = df.iloc[idx].astype(str).str.lower().tolist()
            if any(p in str(c) for c in row_vals for p in possible_header_keywords):
                header_idx = idx
                break
                
        df.columns = df.iloc[header_idx]
        df = df.iloc[header_idx+1:].reset_index(drop=True)
            
        print("Fixed columns:", list(df.columns))

        # -----------------------------
        # CLEAN COLUMN NAMES
        # -----------------------------
        df.columns = df.columns.astype(str).str.lower().str.strip()
        df = df.dropna(how="all", subset=df.columns)

        print("Cleaned shape:", df.shape)

        # -----------------------------
        # FIND DESCRIPTION COLUMN
        # -----------------------------
        possible_cols = ["description", "narration", "name", "details", "transaction"]

        desc_col = None
        for col in possible_cols:
            matches = [c for c in df.columns if col in c]
            if matches:
                desc_col = matches[0]
                break

        if not desc_col:
            return {"error": f"No transaction description column found. Found: {list(df.columns)}"}

        df["description"] = df[desc_col].astype(str)

        # -----------------------------
        # CLASSIFY
        # -----------------------------
        df["category"] = df["description"].apply(classify_transaction)

        # -----------------------------
        # FIX NaN FOR JSON
        # -----------------------------
        df = df.replace({np.nan: None})

        # -----------------------------
        # SUMMARY (FOR DASHBOARD)
        # -----------------------------
        summary = df["category"].value_counts().to_dict()

        return {
            "total_transactions": len(df),
            "summary": summary,
            "transactions": df.to_dict(orient="records")
        }

    except Exception as e:
        print("\nERROR")
        traceback.print_exc()

        return {
            "error": "Internal Server Error",
            "details": str(e)
        }