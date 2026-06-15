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
   → that is the header row.
5. Build the dataframe: header row names the columns; data = rows from
   first_data_row onwards.
6. Detect column roles by CONTENT:
     • date_col   → column with highest fraction of date-like values
     • amount_col → column(s) with highest fraction of numeric values
                    (keyword "debit"/"credit" used only to split the two)
     • narr_col   → among remaining columns, the one with the highest
                    "text richness" score (long, diverse, non-numeric strings)
7. Nuclear fallback: if all extracted amounts are still 0, scan every
   unassigned column for non-zero numeric values and use the best one.
"""

import re
import uuid
import datetime as _dt
import pandas as pd
from io import BytesIO
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from models.database import get_db, Transaction, UploadSession, User
from routes.auth import get_current_user
from services.classifier import classify_batch

# PDF support — imported lazily so missing package gives a clear error at upload time
try:
    import pdfplumber as _pdfplumber
    from pdfminer.pdfdocument import PDFPasswordIncorrect as _PDFPasswordIncorrect
    _PDF_AVAILABLE = True
except ImportError:
    _PDF_AVAILABLE = False
    _PDFPasswordIncorrect = None

router = APIRouter()

# ── regexes ──────────────────────────────────────────────────────────────────
_DATE_RE = re.compile(
    r"(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})"           # 01/01/2024  01-01-24
    r"|(\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2})"             # 2024-01-01  2024/01/01
    r"|(\d{1,2}[/\-\.][A-Za-z]{3,9}[/\-\.]\d{2,4})"     # 01-Jan-2024  01/January/24
    r"|(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4})"             # 01 Jan 2024
    r"|([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{2,4})",          # Jan 01, 2024
    re.IGNORECASE,
)

# Strings treated as "empty" in amount cells
_NULL_VALS = {"", "--", "-", "nil", "n/a", "none", "nan", "null"}

_MIN_DESC_LEN = 4

# Keywords that strongly indicate an incoming credit / income transaction
_INCOME_RE = re.compile(
    r"\b(salary|payroll|wages|credit\s*alert|inflow|reversal|refund|"
    r"dividend|interest\s*earned|commission\s*(earned|credit)|"
    r"lodgment|cash\s*deposit|transfer\s*(in|from)|"
    r"money\s*received|payment\s*received|reimbursement)\b",
    re.IGNORECASE,
)


# ── primitive helpers ─────────────────────────────────────────────────────────

def _clean(v) -> str:
    return str(v).strip()


def _is_date(v: str) -> bool:
    s = _clean(v)
    return bool(_DATE_RE.search(s)) and len(s) >= 6


def _strip_amount(raw: str) -> str:
    """Normalise an amount string to a plain float-parseable form."""
    s = re.sub(r"(?i)^\s*ngn\s*", "", raw)      # strip leading "NGN" before other chars
    s = re.sub(r"[₦N$,\s]", "", s)              # strip currency symbols + commas + spaces
    s = re.sub(r"(?i)\(?cr\)?$", "", s)         # trailing CR / (CR)
    s = re.sub(r"(?i)dr$", "", s)               # trailing DR
    if s.startswith("(") and s.endswith(")"):   # (1234.56) → 1234.56
        s = s[1:-1]
    if s.endswith("-"):                          # 1234.56- → 1234.56
        s = s[:-1]
    if s.startswith("-"):                        # strip leading minus (sign handled elsewhere)
        s = s[1:]
    return s


def _is_number(v: str) -> bool:
    s = _strip_amount(_clean(v))
    if not s or s.lower() in _NULL_VALS:
        return False
    try:
        float(s)
        return True
    except (ValueError, TypeError):
        return False


def _to_float(v) -> float:
    s = _strip_amount(_clean(v))
    try:
        return abs(float(s))
    except (ValueError, TypeError):
        return 0.0


def _amount_is_credit(raw: str) -> bool:
    """
    Return True when the raw cell value signals an incoming credit:
      • ends with CR / (CR) suffix
      • starts with a minus sign (some banks negate credits)
      • is a parenthetical negative (accounting format)
    """
    s = _clean(raw)
    if re.search(r"(?i)\(?cr\)?$", s):
        return True
    stripped = re.sub(r"[₦N$,\s]", "", s)
    if stripped.startswith("-") or (stripped.startswith("(") and stripped.endswith(")")):
        return True
    return False


def _col_norm(col: str) -> str:
    """Lower-case, replace non-alnum with underscore."""
    return re.sub(r"[^a-z0-9]", "_", str(col).lower().strip())


def _kw_match(col: str, keywords: list[str]) -> bool:
    """
    True if any keyword is a whole-word substring of the normalised col name.
    Short keywords (≤2 chars) must appear as standalone tokens.
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


# ── step 1 + 2 + 3: find the transaction section ─────────────────────────────

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
        score = len(set(text_vals))
        if score > best_score:
            best_score = score
            best_row = r

    return best_row if best_score >= 1 else None


# ── step 4: build the named dataframe ─────────────────────────────────────────

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


# ── step 5: detect column roles by content ────────────────────────────────────

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

        rich = [v for v in non_null
                if not _is_date(v) and not _is_number(v) and len(v) >= _MIN_DESC_LEN]
        if rich:
            avg_len    = sum(len(v) for v in rich) / len(rich)
            uniqueness = len(set(v.lower() for v in rich)) / len(rich)
            text_score[col] = avg_len * uniqueness * len(rich) / n
        else:
            text_score[col] = 0.0

    assigned: set[str] = set()

    # ── date column ───────────────────────────────────────────────────────────
    date_candidates = sorted(cols, key=lambda c: date_frac[c], reverse=True)
    date_col = None
    if date_candidates and date_frac[date_candidates[0]] >= 0.2:
        primary = [c for c in date_candidates
                   if date_frac[c] >= 0.2 and _kw_match(c, ["date", "trans_date", "value_date"])]
        date_col = primary[0] if primary else date_candidates[0]
    assigned.add(date_col)

    # ── amount columns ────────────────────────────────────────────────────────
    # Exclude known balance columns — they have high number_frac but are not transaction amounts
    balance_kw = ["balance", "bal", "closing", "running_bal", "ledger_bal", "avail"]

    num_cols = [
        c for c in cols
        if c not in assigned and number_frac[c] >= 0.10
        and not _kw_match(c, balance_kw)
    ]

    # Fallback: if nothing met threshold, include balance-named cols too
    if not num_cols:
        num_cols = [c for c in cols if c not in assigned and number_frac[c] >= 0.05]

    # Last resort: take the column with the highest numeric fraction
    if not num_cols:
        candidates = [(c, number_frac[c]) for c in cols if c not in assigned]
        if candidates:
            best_c, best_f = max(candidates, key=lambda x: x[1])
            if best_f > 0:
                num_cols = [best_c]

    debit_col = credit_col = amount_col = None

    if num_cols:
        debit_kw  = ["debit", "withdrawal", "dr", "debit_amount", "outflow", "paid_out", "charge"]
        credit_kw = ["credit", "deposit", "credit_amount", "inflow", "paid_in", "cr"]
        amt_kw    = ["amount", "naira", "ngn", "transaction_amount", "trans_amount", "value"]

        for c in num_cols:
            if debit_col  is None and _kw_match(c, debit_kw):
                debit_col  = c
            elif credit_col is None and _kw_match(c, credit_kw):
                credit_col = c
            elif amount_col is None and _kw_match(c, amt_kw):
                amount_col = c

        # No keywords matched — pick the best candidates
        if debit_col is None and credit_col is None and amount_col is None:
            if len(num_cols) == 1:
                amount_col = num_cols[0]
            else:
                # Among multiple candidates, prefer columns with moderate density
                # (balance columns are ~100% populated; debit/credit cols have gaps)
                def _col_score(c: str) -> float:
                    nf = number_frac[c]
                    return nf if nf <= 0.90 else nf - 1.5   # penalise near-100% density

                scored = sorted(num_cols, key=_col_score, reverse=True)
                amount_col = scored[0]
                # If two columns left with similar scores, treat as debit/credit split
                if len(scored) >= 2 and _col_score(scored[1]) > 0.15:
                    debit_col  = scored[0]
                    credit_col = scored[1]
                    amount_col = None

    for c in (debit_col, credit_col, amount_col):
        if c:
            assigned.add(c)

    # ── narration / description column ────────────────────────────────────────
    narr_kw = ["narration", "description", "details", "particular",
               "memo", "remark", "transaction_detail", "trans_detail",
               "narr", "desc", "transaction", "remarks", "reference"]

    remaining = [c for c in cols if c not in assigned]
    narr_col  = None

    if remaining:
        for c in remaining:
            if _kw_match(c, narr_kw) and text_score.get(c, 0) > 0:
                narr_col = c
                break

        if narr_col is None:
            scored = [(c, text_score.get(c, 0)) for c in remaining]
            scored.sort(key=lambda x: x[1], reverse=True)
            if scored and scored[0][1] > 0:
                narr_col = scored[0][0]

        if narr_col is None and remaining:
            narr_col = remaining[0]

    return {
        "date":   date_col,
        "narr":   narr_col,
        "debit":  debit_col,
        "credit": credit_col,
        "amount": amount_col,
    }


# ── step 6: read the raw file ─────────────────────────────────────────────────

def _cell_to_str(x) -> str:
    """Convert any Excel cell value to a clean string."""
    if x is None:
        return ""
    if isinstance(x, float):
        if x != x:   # NaN
            return ""
        try:
            i = int(x)
            if float(i) == x:
                return str(i)
        except (OverflowError, ValueError):
            pass
        return str(x)
    if isinstance(x, (_dt.datetime, _dt.date)):
        return x.strftime("%d/%m/%Y")
    if isinstance(x, bool):
        return str(int(x))
    if isinstance(x, int):
        return str(x)
    return str(x).strip()


# ── PDF helpers ───────────────────────────────────────────────────────────────

def _is_pdf_password_error(exc: Exception) -> bool:
    if _PDFPasswordIncorrect and isinstance(exc, _PDFPasswordIncorrect):
        return True
    name = type(exc).__name__.lower()
    msg  = str(exc).lower()
    return "password" in name or "password" in msg or "encrypt" in msg or "decrypt" in msg


def _pdf_tables_to_rows(pdf) -> list[list[str]]:
    """
    Try three extraction strategies in order of reliability and return
    the first that yields non-empty structured rows.
    """
    strategies = [
        {},                                                                    # pdfplumber auto
        {"vertical_strategy": "lines",   "horizontal_strategy": "lines"},    # bordered tables
        {"vertical_strategy": "text",    "horizontal_strategy": "text"},      # text-aligned cols
    ]
    for settings in strategies:
        all_rows: list[list[str]] = []
        for page in pdf.pages:
            try:
                tables = page.extract_tables(settings)
                for table in (tables or []):
                    for row in table:
                        cleaned = [str(c).strip() if c else "" for c in row]
                        if any(cleaned):
                            all_rows.append(cleaned)
            except Exception:
                continue
        if all_rows:
            return all_rows
    return []


def _pdf_words_to_rows(pdf) -> list[list[str]]:
    """
    Fall back: extract individual words with bounding boxes, cluster them
    into lines and columns, and reconstruct a table-like row list.
    """
    all_words: list[dict] = []
    for page in pdf.pages:
        try:
            words = page.extract_words(x_tolerance=5, y_tolerance=5)
            for w in words:
                all_words.append({
                    "text": w["text"],
                    "x0":   w["x0"],
                    "top":  w["top"],
                    "page": page.page_number,
                })
        except Exception:
            continue

    if not all_words:
        return []

    # Sort by page → vertical position → horizontal position
    all_words.sort(key=lambda w: (w["page"], round(w["top"]), w["x0"]))

    # Cluster into lines (words within 6 pt vertically on the same page)
    lines: list[list[dict]] = []
    cur:   list[dict]        = [all_words[0]]
    for w in all_words[1:]:
        if w["page"] == cur[0]["page"] and abs(w["top"] - cur[0]["top"]) <= 6:
            cur.append(w)
        else:
            lines.append(cur)
            cur = [w]
    if cur:
        lines.append(cur)

    # Detect column boundaries by clustering all x0 values (gap > 18 pt = new col)
    x0s = sorted(w["x0"] for w in all_words)
    col_starts = [x0s[0]] if x0s else []
    for x in x0s[1:]:
        if x - col_starts[-1] > 18:
            col_starts.append(x)

    if len(col_starts) < 2:
        # Cannot detect columns — return each line as a single-cell row
        return [[" ".join(w["text"] for w in line)] for line in lines]

    def _col_idx(x0: float) -> int:
        return min(range(len(col_starts)), key=lambda i: abs(col_starts[i] - x0))

    n_cols = len(col_starts)
    rows: list[list[str]] = []
    for line in lines:
        row = [""] * n_cols
        for w in line:
            i = _col_idx(w["x0"])
            row[i] = (row[i] + " " + w["text"]).strip()
        if any(row):
            rows.append(row)
    return rows


def _read_pdf(content: bytes, password: str = "") -> pd.DataFrame:
    """Open a PDF and extract its transaction table as a raw DataFrame."""
    if not _PDF_AVAILABLE:
        raise HTTPException(
            status_code=400,
            detail="PDF support is not available on this server. Please upload a CSV or Excel file.",
        )

    # Open — raises PDFPasswordIncorrect when password is wrong / missing
    try:
        pdf_file = _pdfplumber.open(BytesIO(content), password=password or "")
    except Exception as exc:
        if _is_pdf_password_error(exc):
            raise HTTPException(status_code=422, detail="PDF_NEEDS_PASSWORD")
        raise HTTPException(status_code=400, detail=f"Cannot open PDF: {exc}") from exc

    try:
        with pdf_file as pdf:
            # Strategy 1 & 2 & 3: table extraction with three rule-sets
            rows = _pdf_tables_to_rows(pdf)

            # Strategy 4: word-position column reconstruction
            if not rows:
                rows = _pdf_words_to_rows(pdf)

            # Strategy 5: raw text lines (last resort)
            if not rows:
                for page in pdf.pages:
                    try:
                        text = page.extract_text() or ""
                        for line in text.splitlines():
                            if line.strip():
                                rows.append([line.strip()])
                    except Exception:
                        continue

    except HTTPException:
        raise
    except Exception as exc:
        if _is_pdf_password_error(exc):
            raise HTTPException(status_code=422, detail="PDF_NEEDS_PASSWORD")
        raise HTTPException(status_code=400, detail=f"Cannot read PDF: {exc}") from exc

    if not rows:
        raise HTTPException(
            status_code=400,
            detail="No readable content found in this PDF. "
                   "Scanned / image-based PDFs are not supported.",
        )

    # Pad all rows to the same width and convert to DataFrame
    max_cols = max(len(r) for r in rows)
    padded   = [r + [""] * (max_cols - len(r)) for r in rows]
    return pd.DataFrame(padded).fillna("").astype(str)


def _read_raw(content: bytes, filename: str, password: str = "") -> pd.DataFrame:
    try:
        if filename.endswith(".pdf"):
            return _read_pdf(content, password)
        elif filename.endswith(".csv"):
            raw = pd.read_csv(BytesIO(content), header=None, dtype=str, on_bad_lines="skip")
        else:
            # Read Excel without dtype constraint so openpyxl preserves date/number types,
            # then convert each cell to a clean string with _cell_to_str.
            raw = pd.read_excel(BytesIO(content), header=None)
            for col_i in raw.columns:
                raw[col_i] = raw[col_i].apply(_cell_to_str)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Cannot read file: {exc}") from exc
    return raw.fillna("").astype(str)


# ── route ─────────────────────────────────────────────────────────────────────

@router.post("")
async def upload_transactions(
    file: UploadFile = File(...),
    pdf_password: str = Form(default=""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content  = await file.read()
    filename = (file.filename or "").lower()

    if not filename.endswith((".csv", ".xlsx", ".xls", ".pdf")):
        raise HTTPException(status_code=400, detail="Only CSV, Excel, and PDF files are supported.")

    raw = _read_raw(content, filename, password=pdf_password)
    if raw.empty:
        raise HTTPException(status_code=400, detail="The file is empty.")

    # ── locate the transaction section ────────────────────────────────────────
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

    # ── extract transactions (first pass) ─────────────────────────────────────
    # Store (desc, date, row_dict) so nuclear fallback can access any column.
    extracted: list[tuple[str, str, dict]] = []

    for _, row in df.iterrows():
        desc = _clean(row.get(cols["narr"], "") if cols["narr"] else "")
        if not desc or desc.lower() in _NULL_VALS:
            continue
        if len(desc) < _MIN_DESC_LEN:
            continue
        if "owealth" in desc.lower():
            continue
        if _kw_match(desc, ["narration", "description", "details", "particular",
                              "date", "debit", "credit", "balance", "reference"]):
            if len(desc) < 12:
                continue

        dt = ""
        if cols["date"]:
            raw_dt = _clean(row.get(cols["date"], ""))
            dt = "" if raw_dt.lower() in _NULL_VALS else raw_dt

        extracted.append((desc, dt, dict(row)))

    if not extracted:
        raise HTTPException(
            status_code=400,
            detail="No valid transaction rows found. "
                   "Please ensure your file has a narration/description column.",
        )

    # ── extract amounts ───────────────────────────────────────────────────────
    amounts:  list[float] = []
    tx_types: list[str]   = []

    for desc, _dt_val, row in extracted:
        amt     = 0.0
        tx_type = "debit"

        if cols["debit"]:
            raw_cell = str(row.get(cols["debit"], ""))
            v = _to_float(raw_cell)
            if v > 0:
                amt     = v
                tx_type = "credit" if _amount_is_credit(raw_cell) else "debit"

        if amt == 0.0 and cols["credit"]:
            v = _to_float(str(row.get(cols["credit"], "")))
            if v > 0:
                amt, tx_type = v, "credit"

        if amt == 0.0 and cols["amount"]:
            raw_cell = str(row.get(cols["amount"], ""))
            v = _to_float(raw_cell)
            if v > 0:
                amt     = v
                tx_type = "credit" if (
                    _amount_is_credit(raw_cell) or _INCOME_RE.search(desc)
                ) else "debit"

        amounts.append(amt)
        tx_types.append(tx_type)

    # ── nuclear fallback: if ALL amounts are 0 scan every other column ────────
    if all(a == 0.0 for a in amounts):
        used_cols = {c for c in [cols["date"], cols["narr"],
                                  cols["debit"], cols["credit"], cols["amount"]] if c}
        best_col   = None
        best_count = 0

        for fc in df.columns:
            if fc in used_cols:
                continue
            nz = sum(1 for _, _, row in extracted if _to_float(str(row.get(fc, ""))) > 0)
            if nz > best_count:
                best_count = nz
                best_col   = fc

        if best_col and best_count > 0:
            amounts   = []
            tx_types  = []
            for desc, _dt_val, row in extracted:
                raw_cell = str(row.get(best_col, ""))
                v        = _to_float(raw_cell)
                amounts.append(v)
                tx_types.append(
                    "credit" if (_amount_is_credit(raw_cell) or _INCOME_RE.search(desc))
                    else "debit"
                )

    descriptions = [e[0] for e in extracted]
    dates        = [e[1] for e in extracted]

    # ── classify and save ─────────────────────────────────────────────────────
    classifications = classify_batch(descriptions)
    session_id = str(uuid.uuid4())

    for desc, amt, dt, tx_type, clf in zip(descriptions, amounts, dates, tx_types, classifications):
        db.add(Transaction(
            user_id=current_user.id,
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

    # Build session summary
    total_spend  = sum(t.amount for t in saved if t.transaction_type == "debit")
    total_income = sum(t.amount for t in saved if t.transaction_type == "credit")
    all_dates    = sorted([t.date for t in saved if t.date and t.date not in ("", "nan", "None")])
    date_start   = all_dates[0]  if all_dates else None
    date_end     = all_dates[-1] if all_dates else None

    cat_totals: dict[str, float] = {}
    for t in saved:
        if t.transaction_type == "debit":
            cat = t.corrected_category if t.is_corrected else t.predicted_category
            cat_totals[cat] = cat_totals.get(cat, 0.0) + (t.amount or 0.0)
    top_cat = max(cat_totals, key=lambda k: cat_totals[k]) if cat_totals else None

    db.add(UploadSession(
        user_id=current_user.id,
        session_id=session_id,
        filename=file.filename or "unknown",
        total_transactions=len(saved),
        total_spend=round(total_spend, 2),
        total_income=round(total_income, 2),
        date_range_start=date_start,
        date_range_end=date_end,
        top_category=top_cat,
    ))
    db.commit()

    return {
        "session_id":   session_id,
        "total":        len(saved),
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
