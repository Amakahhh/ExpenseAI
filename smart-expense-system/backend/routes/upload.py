"""
upload.py — Universal bank statement parser.

Works for ANY bank format by treating column detection as a content-analysis
problem, not a header-keyword problem.

Algorithm
─────────
1. Read the raw file with no assumed header row.
2. Find the "date column": the column whose cells contain the most date-like
   values (regex-matched).
3. Find the first row in the date column that actually contains a date
   → that is where the transaction data starts (first_data_row).
4. Look at EVERY row before first_data_row and pick the one with the
   most distinct, non-date, non-amount text values
   → that is the header row.  (A full 6-column header beats a 2-column
   mini-header from the metadata section.)
5. Build the dataframe: header row names the columns; data = rows from
   first_data_row onwards.
6. Detect column roles by CONTENT:
     • date_col   → column with highest fraction of date-like values
     • amount_col → column(s) with highest fraction of numeric values
                    (keyword "debit"/"credit" used only to split the two)
     • narr_col   → among remaining columns, the one with the highest
                    "text richness" score (long, diverse, non-numeric strings)
7. If narr_col is still None, relax and try the next-best text column.
8. Extract rows, skipping blanks and header-repetition rows.
"""

import re
import uuid
import pandas as pd
from io import BytesIO
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from models.database import get_db, Transaction
from services.classifier import classify_batch

router = APIRouter()

# ── regexes ──────────────────────────────────────────────────────────────────
_DATE_RE = re.compile(
    r"(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})"
    r"|(\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2})"
    r"|(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4})"
    r"|([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{2,4})",
    re.IGNORECASE,
)

_NUMBER_RE = re.compile(r"^[₦$]?[\d,]+\.?\d*$")   # matches "5,000.00", "₦3500"

# Strings treated as "empty" in amount cells
_NULL_VALS = {"", "--", "-", "nil", "n/a", "none", "nan"}

_MIN_DESC_LEN = 4   # minimum chars for a valid description

# Keywords that strongly indicate an incoming credit / income transaction.
# Used only when the file has a single combined amount column (no separate debit/credit cols).
_INCOME_RE = re.compile(
    r"\b(salary|payroll|wages|credit\s*alert|inflow|reversal|refund|"
    r"dividend|interest\s*earned|commission\s*(earned|credit)|"
    r"lodgment|cash\s*deposit|transfer\s*(in|from)|"
    r"money\s*received|payment\s*received|reimbursement)\b",
    re.IGNORECASE,
)


# ── primitive helpers ────────────────────────────────────────────────────────

def _clean(v) -> str:
    return str(v).strip()


def _is_date(v: str) -> bool:
    s = _clean(v)
    return bool(_DATE_RE.search(s)) and len(s) >= 6


def _is_number(v: str) -> bool:
    s = re.sub(r"[₦,\s]", "", _clean(v))
    s = re.sub(r"(?i)(dr|cr)$", "", s)
    if not s or s in _NULL_VALS:
        return False
    return bool(_NUMBER_RE.match(s))


def _to_float(v) -> float:
    s = re.sub(r"[₦,\s]", "", _clean(v))
    s = re.sub(r"(?i)(dr|cr)$", "", s)
    try:
        return abs(float(s))
    except (ValueError, TypeError):
        return 0.0


def _amount_is_credit(raw: str) -> bool:
    """
    Return True when the raw cell value signals an incoming credit:
      - ends with CR / (CR) suffix  → e.g. "5,000.00CR" or "5,000.00 (CR)"
      - starts with a minus sign    → e.g. "-5000" (some banks negate credits)
    Both conventions are used by different Nigerian banks.
    """
    s = _clean(raw)
    if re.search(r"(?i)\(?cr\)?$", s):
        return True
    stripped = re.sub(r"[₦,\s]", "", s)
    if stripped.startswith("-"):
        return True
    return False


def _col_norm(col: str) -> str:
    """Lower-case, replace non-alnum with underscore."""
    return re.sub(r"[^a-z0-9]", "_", str(col).lower().strip())


def _kw_match(col: str, keywords: list[str]) -> bool:
    """
    True if any keyword is a whole-word substring of the normalised col name.
    Short keywords (≤2 chars) must appear as standalone tokens to avoid
    e.g. 'cr' matching inside 'description'.
    """
    norm = _col_norm(col)
    for kw in keywords:
        if len(kw) <= 2:
            if re.search(r"(^|_)" + re.escape(kw) + r"($|_)", norm):
                return True
        else:
            if kw in norm:
                return True
    return False


# ── step 1 + 2 + 3: find the transaction section ────────────────────────────

def _find_date_col_idx(raw: pd.DataFrame) -> int:
    """Return the column index with the most date-like values."""
    scores = [
        sum(_is_date(_clean(raw.iloc[r, c])) for r in range(len(raw)))
        for c in range(raw.shape[1])
    ]
    if max(scores, default=0) == 0:
        return 0
    return scores.index(max(scores))


def _find_first_data_row(raw: pd.DataFrame, date_col_idx: int) -> int:
    """First row index where the date column contains a real date."""
    for r in range(len(raw)):
        if _is_date(_clean(raw.iloc[r, date_col_idx])):
            return r
    return 0


def _find_best_header_row(raw: pd.DataFrame, first_data_row: int) -> int | None:
    """
    Among all rows BEFORE first_data_row, return the index of the one with
    the most distinct, non-date, non-number text tokens.

    A full-column header ("Date | Narration | Debit | Credit | Balance")
    scores higher than a 2-column metadata mini-header ("Credit(₦) | Value Date").
    """
    best_row, best_score = None, 0

    for r in range(first_data_row):
        vals = [_clean(raw.iloc[r, c]) for c in range(raw.shape[1])]
        text_vals = [
            v for v in vals
            if v and v.lower() not in _NULL_VALS
            and not _is_date(v)
            and not _is_number(v)
        ]
        score = len(set(text_vals))   # unique non-date, non-number strings
        if score > best_score:
            best_score = score
            best_row = r

    return best_row if best_score >= 1 else None


# ── step 4: build the named dataframe ────────────────────────────────────────

def _build_named_df(raw: pd.DataFrame, header_row: int | None,
                    first_data_row: int) -> pd.DataFrame:
    n_cols = raw.shape[1]

    if header_row is not None:
        names = [
            _clean(raw.iloc[header_row, c]) or f"col_{c}"
            for c in range(n_cols)
        ]
    else:
        names = [f"col_{c}" for c in range(n_cols)]

    df = raw.iloc[first_data_row:].copy()
    df.columns = names
    return df.dropna(how="all").reset_index(drop=True)


# ── step 5: detect column roles by content ───────────────────────────────────

def _analyse_columns(df: pd.DataFrame) -> dict:
    """
    Return {'date', 'narr', 'debit', 'credit', 'amount'} column name dict.
    Detection is content-first; column-name keywords are used only to split
    ambiguous cases (e.g. debit vs credit when both are numeric columns).
    """
    cols = df.columns.tolist()

    date_frac   = {}
    number_frac = {}
    text_score  = {}

    for col in cols:
        vals = df[col].astype(str).str.strip().tolist()
        non_null = [v for v in vals if v and v.lower() not in _NULL_VALS]
        n = len(non_null) or 1

        date_frac[col]   = sum(_is_date(v)   for v in non_null) / n
        number_frac[col] = sum(_is_number(v) for v in non_null) / n

        # Text-richness: avg length of strings that are NOT dates and NOT numbers
        rich = [v for v in non_null
                if not _is_date(v) and not _is_number(v) and len(v) >= _MIN_DESC_LEN]
        # Multiply avg-len by uniqueness ratio to reward diverse narrations
        if rich:
            avg_len     = sum(len(v) for v in rich) / len(rich)
            uniqueness  = len(set(v.lower() for v in rich)) / len(rich)
            text_score[col] = avg_len * uniqueness * len(rich) / n
        else:
            text_score[col] = 0.0

    assigned: set[str] = set()

    # ── date column ──────────────────────────────────────────────────────────
    # Pick the column with the highest fraction of date values.
    # Prefer "date" or "trans_date" over "value_date" / "posting_date" as
    # tie-breaker (the former is usually the transaction date).
    date_candidates = sorted(cols, key=lambda c: date_frac[c], reverse=True)
    date_col = None
    if date_candidates and date_frac[date_candidates[0]] >= 0.2:
        # Among top-scoring date cols, prefer one named just "date"
        primary = [c for c in date_candidates
                   if date_frac[c] >= 0.2 and _kw_match(c, ["date", "trans_date"])]
        date_col = primary[0] if primary else date_candidates[0]
    assigned.add(date_col)

    # ── amount columns ───────────────────────────────────────────────────────
    # Find all columns with high numeric fraction (excluding the date column).
    num_cols = [
        c for c in cols
        if c not in assigned and number_frac[c] >= 0.25
    ]

    debit_col = credit_col = amount_col = None

    if num_cols:
        # Try to split into debit / credit by keyword
        debit_kw  = ["debit", "withdrawal", "dr", "debit_amount"]
        credit_kw = ["credit", "deposit", "credit_amount"]
        amt_kw    = ["amount", "naira", "ngn", "transaction_amount"]

        for c in num_cols:
            if debit_col  is None and _kw_match(c, debit_kw):
                debit_col  = c
            elif credit_col is None and _kw_match(c, credit_kw):
                credit_col = c
            elif amount_col is None and _kw_match(c, amt_kw):
                amount_col = c

        # No keywords matched — use the numeric column with the highest non-zero rate
        if debit_col is None and credit_col is None and amount_col is None:
            best_num = max(num_cols, key=lambda c: number_frac[c])
            amount_col = best_num

    for c in (debit_col, credit_col, amount_col):
        if c:
            assigned.add(c)

    # ── narration / description column ───────────────────────────────────────
    # Among columns NOT yet assigned, pick the one with the highest text_score.
    # A keyword match is used as a tie-breaker, not a gate.
    narr_kw = ["narration", "description", "details", "particular",
               "memo", "remark", "transaction_detail", "trans_detail",
               "narr", "desc", "transaction"]

    remaining = [c for c in cols if c not in assigned]
    narr_col  = None

    if remaining:
        # Keyword-named column first (if its text_score is non-zero)
        for c in remaining:
            if _kw_match(c, narr_kw) and text_score.get(c, 0) > 0:
                narr_col = c
                break

        # Otherwise pick by content score
        if narr_col is None:
            scored = [(c, text_score.get(c, 0)) for c in remaining]
            scored.sort(key=lambda x: x[1], reverse=True)
            if scored and scored[0][1] > 0:
                narr_col = scored[0][0]

        # Last resort: if all text_scores are 0 (e.g. file has only 2 columns),
        # use whatever is not the date or amount col — even if it has dates.
        if narr_col is None and remaining:
            narr_col = remaining[0]

    return {
        "date":   date_col,
        "narr":   narr_col,
        "debit":  debit_col,
        "credit": credit_col,
        "amount": amount_col,
    }


# ── step 6: read the raw file ────────────────────────────────────────────────

def _read_raw(content: bytes, filename: str) -> pd.DataFrame:
    kw = dict(header=None, dtype=str)
    try:
        if filename.endswith(".csv"):
            raw = pd.read_csv(BytesIO(content), **kw, on_bad_lines="skip")
        else:
            raw = pd.read_excel(BytesIO(content), **kw)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Cannot read file: {exc}") from exc
    return raw.fillna("").astype(str)


# ── route ────────────────────────────────────────────────────────────────────

@router.post("")
async def upload_transactions(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    content  = await file.read()
    filename = (file.filename or "").lower()

    if not filename.endswith((".csv", ".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only CSV and Excel files are supported.")

    raw = _read_raw(content, filename)
    if raw.empty:
        raise HTTPException(status_code=400, detail="The file is empty.")

    # ── locate the transaction section ───────────────────────────────────────
    date_col_idx   = _find_date_col_idx(raw)
    first_data_row = _find_first_data_row(raw, date_col_idx)
    header_row     = _find_best_header_row(raw, first_data_row)

    df = _build_named_df(raw, header_row, first_data_row)
    if df.empty:
        raise HTTPException(status_code=400, detail="No data rows found.")

    # ── detect column roles ───────────────────────────────────────────────────
    cols = _analyse_columns(df)

    if cols["narr"] is None and cols["date"] is None:
        raise HTTPException(
            status_code=400,
            detail="Could not identify transaction columns. "
                   "Ensure the file has Date, Description, and Amount columns.",
        )

    # ── extract transactions ──────────────────────────────────────────────────
    descriptions, amounts, dates, tx_types = [], [], [], []

    for _, row in df.iterrows():
        # Description
        desc = _clean(row.get(cols["narr"], "") if cols["narr"] else "")
        if not desc or desc.lower() in _NULL_VALS:
            continue
        if len(desc) < _MIN_DESC_LEN:
            continue
        # Skip OWealth internal fund movements — not real expenses or income
        if "owealth" in desc.lower():
            continue
        # Skip rows where the narration column contains a column-header label
        # (some bank exports repeat the header mid-table)
        if _kw_match(desc, ["narration", "description", "details", "particular",
                              "date", "debit", "credit", "balance", "reference"]):
            if len(desc) < 12:   # short header word, not a real transaction
                continue

        # Date
        dt = ""
        if cols["date"]:
            raw_dt = _clean(row.get(cols["date"], ""))
            dt = "" if raw_dt.lower() in _NULL_VALS else raw_dt

        # Amount + transaction_type
        # Priority: debit col → expense; credit col → income; amount col → multi-signal infer
        amt = 0.0
        tx_type = "debit"

        if cols["debit"]:
            raw_cell = str(row.get(cols["debit"], ""))
            v = _to_float(raw_cell)
            if v > 0:
                # A value in the debit column with a CR suffix is actually income
                amt = v
                tx_type = "credit" if _amount_is_credit(raw_cell) else "debit"

        if amt == 0.0 and cols["credit"]:
            v = _to_float(row.get(cols["credit"], ""))
            if v > 0:
                amt, tx_type = v, "credit"

        if amt == 0.0 and cols["amount"]:
            raw_cell = str(row.get(cols["amount"], ""))
            v = _to_float(raw_cell)
            if v > 0:
                amt = v
                # Three independent signals — any one is enough to call it income
                tx_type = "credit" if (
                    _amount_is_credit(raw_cell) or _INCOME_RE.search(desc)
                ) else "debit"

        descriptions.append(desc)
        amounts.append(amt)
        dates.append(dt)
        tx_types.append(tx_type)

    if not descriptions:
        raise HTTPException(
            status_code=400,
            detail="No valid transaction rows found. "
                   "Please ensure your file has a narration/description column.",
        )

    # ── classify and save ─────────────────────────────────────────────────────
    classifications = classify_batch(descriptions)
    session_id = str(uuid.uuid4())

    for desc, amt, dt, tx_type, clf in zip(descriptions, amounts, dates, tx_types, classifications):
        db.add(Transaction(
            session_id=session_id,
            date=dt,
            description=desc,
            amount=amt,
            predicted_category=clf["category"],
            confidence=clf["confidence"],
            is_corrected=False,
            transaction_type=tx_type,
        ))

    db.commit()

    saved = (
        db.query(Transaction)
        .filter(Transaction.session_id == session_id)
        .order_by(Transaction.id)
        .all()
    )

    return {
        "session_id": session_id,
        "total": len(saved),
        "transactions": [_tx_to_dict(t) for t in saved],
    }


def _tx_to_dict(t: Transaction) -> dict:
    return {
        "id":                 t.id,
        "date":               t.date,
        "description":        t.description,
        "amount":             t.amount,
        "transaction_type":   t.transaction_type or "debit",
        "predicted_category": t.predicted_category,
        "confidence":         t.confidence,
        "is_corrected":       t.is_corrected,
        "corrected_category": t.corrected_category,
    }
