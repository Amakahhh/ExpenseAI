from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from models.database import init_db
from services.classifier import _load_model
from routes import upload, categorize, correct, analytics, transactions
from fastapi import UploadFile, File


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    _load_model()
    yield


app = FastAPI(
    title="Smart Expense Intelligence System",
    description="Nigerian bank transaction classifier — BERT + Prototypical Networks",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router,        prefix="/upload",       tags=["upload"])
app.include_router(categorize.router,    prefix="/categorize",   tags=["categorize"])
app.include_router(correct.router,       prefix="/correct",      tags=["corrections"])
app.include_router(analytics.router,     prefix="/analytics",    tags=["analytics"])
app.include_router(transactions.router,  prefix="/transactions",  tags=["transactions"])


@app.get("/")
def root():
    return {"message": "Smart Expense Intelligence System API", "status": "running"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/debug-parse")
async def debug_parse(file: UploadFile = File(...)):
    """
    Returns what the parser detects about a file without saving anything.
    Use this to diagnose column detection for any bank statement.
    """
    from routes.upload import (
        _read_raw, _find_date_col_idx, _find_first_data_row,
        _find_best_header_row, _build_named_df, _analyse_columns,
    )
    content  = await file.read()
    filename = (file.filename or "").lower()

    try:
        raw = _read_raw(content, filename)
    except Exception as exc:
        return {"error": str(exc)}

    date_col_idx   = _find_date_col_idx(raw)
    first_data_row = _find_first_data_row(raw, date_col_idx)
    header_row     = _find_best_header_row(raw, first_data_row)
    df             = _build_named_df(raw, header_row, first_data_row)
    cols           = _analyse_columns(df)

    sample_rows = []
    for _, row in df.head(5).iterrows():
        sample_rows.append({
            "date":   str(row.get(cols["date"],   "N/A") if cols["date"]   else "N/A"),
            "narr":   str(row.get(cols["narr"],   "N/A") if cols["narr"]   else "N/A"),
            "debit":  str(row.get(cols["debit"],  "N/A") if cols["debit"]  else "N/A"),
            "credit": str(row.get(cols["credit"], "N/A") if cols["credit"] else "N/A"),
        })

    return {
        "total_raw_rows":      len(raw),
        "detected_header_row": header_row,
        "first_data_row":      first_data_row,
        "all_columns":         df.columns.tolist(),
        "assigned_columns":    cols,
        "sample_data":         sample_rows,
    }
