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

# PDF support: pdfplumber → PyMuPDF → Tesseract OCR
try:
    import pdfplumber as _pdfplumber
    _PDFPLUMBER_AVAILABLE = True
except ImportError:
    _PDFPLUMBER_AVAILABLE = False

try:
    import fitz as _fitz          # PyMuPDF ≥ 1.23 — also used for OCR rendering
    _PYMUPDF_AVAILABLE = True
except ImportError:
    _PYMUPDF_AVAILABLE = False

try:
    import pytesseract as _pytesseract
    from PIL import Image as _PILImage
    import io as _io
    # On Windows, Tesseract is often installed but not added to PATH.
    # Point pytesseract at the default install location if the binary is there.
    import os as _os
    _WIN_TESS = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if _os.name == "nt" and _os.path.exists(_WIN_TESS):
        _pytesseract.pytesseract.tesseract_cmd = _WIN_TESS
    _OCR_AVAILABLE = True
except ImportError:
    _OCR_AVAILABLE = False

_PDF_AVAILABLE = _PDFPLUMBER_AVAILABLE or _PYMUPDF_AVAILABLE

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
    if not s or len(s) < 6:
        return False
    m = _DATE_RE.search(s)
    # The date pattern must appear at or near the start of the cell value.
    # This prevents "Statement Period : 01-Dec-2025 to 31-Dec-2025" from
    # being treated as a date cell and triggering the wrong first_data_row.
    return bool(m) and m.start() <= 3


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

def _pdf_is_encrypted(content: bytes) -> bool:
    return b"/Encrypt" in content


def _rows_to_df(rows: list[list[str]]) -> pd.DataFrame:
    max_cols = max(len(r) for r in rows)
    padded   = [r + [""] * (max_cols - len(r)) for r in rows]
    return pd.DataFrame(padded).fillna("").astype(str)


def _words_to_rows(words: list[dict]) -> list[list[str]]:
    """
    Convert a list of word dicts to table rows using ACTUAL inter-word whitespace
    for column detection.

    Each word dict must have: text, x0, x1, top.
    (pdfplumber's extract_words() provides all four; PyMuPDF tuples are
    normalised before calling this function.)

    The key insight: consecutive words within the same table cell have a
    small actual whitespace gap (x0_next − x1_prev ≈ 2–5 pt), while the
    gap between neighbouring columns is typically > 10 pt.  Using x0-to-x0
    distance instead (the old approach) includes word widths (~20–60 pt)
    and falsely treats every word as a new column.
    """
    if not words:
        return []

    words = sorted(words, key=lambda w: (round(w["top"] / 3) * 3, w["x0"]))

    # ── cluster into lines (within 5 pt vertically) ───────────────────────────
    lines: list[list[dict]] = []
    cur: list[dict] = [words[0]]
    for w in words[1:]:
        if abs(w["top"] - cur[0]["top"]) <= 5:
            cur.append(w)
        else:
            lines.append(sorted(cur, key=lambda x: x["x0"]))
            cur = [w]
    if cur:
        lines.append(sorted(cur, key=lambda x: x["x0"]))

    # ── detect column starts using actual whitespace per line ─────────────────
    # For each line: walk left-to-right; when the actual gap (x0_next − x1_prev)
    # exceeds 10 pt, that marks the start of a new column.
    raw_starts: list[float] = []
    for line in lines:
        raw_starts.append(line[0]["x0"])          # first word always starts a column
        for i in range(1, len(line)):
            actual_gap = line[i]["x0"] - line[i - 1]["x1"]
            if actual_gap > 10:
                raw_starts.append(line[i]["x0"])

    # ── cluster raw_starts within 15 pt → final column positions ─────────────
    col_starts: list[float] = []
    for x in sorted(raw_starts):
        if not col_starts or x - col_starts[-1] > 15:
            col_starts.append(x)

    if len(col_starts) < 2:
        return [[" ".join(w["text"] for w in line)] for line in lines]

    def _col_idx(x0: float) -> int:
        return min(range(len(col_starts)), key=lambda i: abs(col_starts[i] - x0))

    rows: list[list[str]] = []
    for line in lines:
        row = [""] * len(col_starts)
        for w in line:
            i = _col_idx(w["x0"])
            row[i] = (row[i] + " " + w["text"]).strip()
        if any(row):
            rows.append(row)
    return rows


# ── OPay-specific extractor ──────────────────────────────────────────────────
#
# OPay PDFs use a fixed 8-column layout with known x-boundaries (in points).
# Descriptions wrap across multiple lines and references split onto a second
# line, so generic table extraction misses most rows.  We use word bounding
# boxes instead: assign each word to a column by x-midpoint, snap y-values
# to a 4 pt grid to group lines, find transaction anchors by their date-time
# pattern, then collect every word in the transaction's vertical band.

_OPAY_COLS: dict[str, tuple[float, float]] = {
    "Trans Time":          (60,  130),
    "Value Date":          (130, 178),
    "Description":         (178, 305),
    "Debit (NGN)":         (295, 342),
    "Credit (NGN)":        (332, 385),
    "Balance After (NGN)": (375, 425),
    "Channel":             (415, 478),
    "Transaction Ref":     (468, 600),
}

# Matches "01 Dec 2025 14:30:00" — the date-time format in OPay's Trans Time column
_OPAY_TIME_RE = re.compile(r"\d{2}\s+\w{3}\s+\d{4}\s+\d{2}:\d{2}:\d{2}")


def _opay_word_col(x_mid: float) -> str | None:
    """Return the column name for a word's x-midpoint, or None if out of range."""
    for col_name, (lo, hi) in _OPAY_COLS.items():
        if lo <= x_mid <= hi:
            return col_name
    return None


def _opay_from_words(pages_words: list[list[dict]]) -> list[list[str]]:
    """
    Core OPay extraction logic.  Takes a list of per-page word lists where
    each word is {text, x0, x1, top} — works with pdfplumber, PyMuPDF, or OCR.
    Returns [] when no OPay date-time pattern is detected (not an OPay PDF).
    """
    all_txns: list[dict] = []

    for words in pages_words:
        if not words:
            continue

        # Tag each word with its snapped y-row and column slot
        for w in words:
            w["_y"]    = round(w["top"] / 4) * 4
            w["_xmid"] = (w["x0"] + w["x1"]) / 2
            w["_col"]  = _opay_word_col(w["_xmid"])

        # Group by snapped y
        y_groups: dict[int, list] = {}
        for w in words:
            y_groups.setdefault(w["_y"], []).append(w)

        # Find transaction anchor rows (Trans Time column contains a datetime)
        tx_ys: list[int] = []
        for y in sorted(y_groups):
            time_words = [w for w in y_groups[y] if w["_col"] == "Trans Time"]
            time_text  = " ".join(w["text"] for w in sorted(time_words, key=lambda x: x["x0"]))
            if _OPAY_TIME_RE.search(time_text):
                tx_ys.append(y)

        if not tx_ys:
            continue

        all_ys = sorted(y_groups)

        for i, tx_y in enumerate(tx_ys):
            next_tx_y = tx_ys[i + 1] if i + 1 < len(tx_ys) else float("inf")

            band: list[dict] = [
                w
                for y in all_ys if tx_y <= y < next_tx_y
                for w in y_groups[y]
            ]

            tx: dict[str, str] = {}
            for col_name in _OPAY_COLS:
                col_words = sorted(
                    [w for w in band if w["_col"] == col_name],
                    key=lambda w: (w["top"], w["x0"]),
                )
                text = " ".join(w["text"] for w in col_words).strip()
                if text == "--" and col_name in ("Debit (NGN)", "Credit (NGN)"):
                    text = ""
                if col_name == "Transaction Ref":
                    text = text.replace(" ", "")
                tx[col_name] = text

            all_txns.append(tx)

    if not all_txns:
        return []

    col_names = list(_OPAY_COLS.keys())
    return [col_names] + [[tx.get(c, "") for c in col_names] for tx in all_txns]


def _opay_extract(pdf) -> list[list[str]]:
    """pdfplumber wrapper: pull words from each page then run _opay_from_words."""
    pages_words = []
    for page in pdf.pages:
        raw = page.extract_words(x_tolerance=3, y_tolerance=3) or []
        pages_words.append([
            {"text": w["text"], "x0": w["x0"], "x1": w["x1"], "top": w["top"]}
            for w in raw
        ])
    return _opay_from_words(pages_words)


# ── OCR extraction (Tesseract fallback) ──────────────────────────────────────
#
# When pdfplumber fails (unusual text encoding, non-standard layout), we render
# each PDF page to a high-resolution image via PyMuPDF then run Tesseract OCR
# to get word bounding boxes.  Digital bank-statement PDFs render perfectly so
# OCR accuracy is near-100 %.  This path handles OPay and any other bank.

def _ocr_page_words(fitz_page, scale: float = 2.5) -> list[dict]:
    """
    Render one PyMuPDF page at `scale`× zoom and run Tesseract word detection.
    Returns [{text, x0, x1, top}] in original PDF-point coordinates.
    """
    mat = _fitz.Matrix(scale, scale)
    pix = fitz_page.get_pixmap(matrix=mat)
    img = _PILImage.frombytes("RGB", [pix.width, pix.height], pix.samples)

    data = _pytesseract.image_to_data(
        img,
        output_type=_pytesseract.Output.DICT,
        config="--psm 6",          # assume uniform text block per page
    )

    words: list[dict] = []
    for i, text in enumerate(data["text"]):
        text = (text or "").strip()
        if not text:
            continue
        conf = int(data["conf"][i])
        if conf < 20:              # discard very low-confidence tokens
            continue
        x  = data["left"][i]  / scale
        y  = data["top"][i]   / scale
        w  = data["width"][i] / scale
        words.append({"text": text, "x0": x, "x1": x + w, "top": y})
    return words


def _read_pdf_ocr(content: bytes, password: str) -> pd.DataFrame:
    """
    OCR-based fallback: renders each page to an image then reads words with
    Tesseract.  Requires PyMuPDF (for rendering) and pytesseract + Tesseract
    binary to be installed.
    """
    if not _PYMUPDF_AVAILABLE:
        raise HTTPException(status_code=500,
                            detail="OCR requires PyMuPDF (pip install pymupdf).")
    if not _OCR_AVAILABLE:
        raise HTTPException(status_code=500,
                            detail="OCR requires pytesseract (pip install pytesseract) "
                                   "and the Tesseract binary.")

    try:
        doc = _fitz.open(stream=content, filetype="pdf")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cannot open PDF: {e}")

    if doc.is_encrypted:
        if not doc.authenticate(password or ""):
            raise HTTPException(status_code=422, detail="PDF_NEEDS_PASSWORD")

    pages_words: list[list[dict]] = []
    for page in doc:
        pages_words.append(_ocr_page_words(page))
    doc.close()

    # Try OPay-specific extraction first
    rows = _opay_from_words(pages_words)

    if not rows:
        # Generic: flatten all page words and detect columns dynamically
        all_words = [w for pw in pages_words for w in pw]
        rows = _words_to_rows(all_words)

    if not rows:
        raise HTTPException(
            status_code=400,
            detail="OCR found no readable text. "
                   "The PDF may be a scanned image with poor quality.",
        )
    return _rows_to_df(rows)


# ── pdfplumber extraction (primary) ──────────────────────────────────────────

def _plumber_page_rows(page) -> list[list[str]]:
    """Extract all table rows from a single pdfplumber page."""

    # Strategy 1 & 2: explicit table detection
    for settings in [
        {"vertical_strategy": "lines",  "horizontal_strategy": "lines"},
        {"vertical_strategy": "text",   "horizontal_strategy": "text",
         "text_x_tolerance": 5, "text_y_tolerance": 5},
    ]:
        try:
            tables = page.extract_tables(settings) or []
            rows: list[list[str]] = []
            for table in tables:
                for row in table:
                    cleaned = [str(c or "").strip() for c in row]
                    if any(cleaned):
                        rows.append(cleaned)
            if rows:
                return rows
        except Exception:
            continue

    # Strategy 3: word-position reconstruction with actual-gap column detection
    try:
        raw_words = page.extract_words(x_tolerance=3, y_tolerance=3) or []
        if raw_words:
            # pdfplumber words already have x0, x1, top, text
            words = [{"text": w["text"], "x0": w["x0"],
                      "x1": w["x1"], "top": w["top"]}
                     for w in raw_words]
            rows = _words_to_rows(words)
            if rows:
                return rows
    except Exception:
        pass

    # Strategy 4: raw text lines (last resort — loses column structure)
    try:
        text = page.extract_text() or ""
        return [[line.strip()] for line in text.splitlines() if line.strip()]
    except Exception:
        return []


def _read_pdf_pdfplumber(content: bytes, password: str) -> pd.DataFrame:
    encrypted = _pdf_is_encrypted(content)
    try:
        with _pdfplumber.open(BytesIO(content), password=password or "") as pdf:
            # Try OPay-specific extraction first; it returns [] for non-OPay PDFs
            all_rows = _opay_extract(pdf)

            if not all_rows:
                # Generic extraction for Wema, GTB, Access, UBA, etc.
                all_rows = []
                for page in pdf.pages:
                    all_rows.extend(_plumber_page_rows(page))
    except HTTPException:
        raise
    except Exception:
        if encrypted:
            raise HTTPException(status_code=422, detail="PDF_NEEDS_PASSWORD")
        raise HTTPException(
            status_code=400,
            detail="Could not read this PDF. The file may be corrupt or password-protected.",
        )
    if not all_rows:
        raise HTTPException(
            status_code=400,
            detail="No readable content found in this PDF. "
                   "Scanned / image-based PDFs are not supported.",
        )
    return _rows_to_df(all_rows)


# ── PyMuPDF extraction (fallback) ────────────────────────────────────────────

def _read_pdf_pymupdf(content: bytes, password: str) -> pd.DataFrame:
    try:
        doc = _fitz.open(stream=content, filetype="pdf")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cannot open PDF: {e}")

    if doc.is_encrypted:
        if not doc.authenticate(password or ""):
            raise HTTPException(status_code=422, detail="PDF_NEEDS_PASSWORD")

    all_rows: list[list[str]] = []

    for page in doc:
        page_rows: list[list[str]] = []

        # Strategy 1: find_tables()
        try:
            for tab in page.find_tables():
                for row in tab.extract():
                    cleaned = [str(cell or "").strip() for cell in row]
                    if any(cleaned):
                        page_rows.append(cleaned)
        except Exception:
            pass

        if not page_rows:
            # Strategy 2: word-position with actual-gap column detection
            try:
                # get_text("words") → (x0,y0,x1,y1,text,block,line,word_no)
                raw = page.get_text("words") or []
                if raw:
                    words = [{"text": w[4], "x0": w[0], "x1": w[2], "top": w[1]}
                             for w in raw]
                    page_rows = _words_to_rows(words)
            except Exception:
                pass

        if not page_rows:
            # Strategy 3: raw text lines
            try:
                for line in (page.get_text("text") or "").splitlines():
                    if line.strip():
                        page_rows.append([line.strip()])
            except Exception:
                pass

        all_rows.extend(page_rows)

    doc.close()

    if not all_rows:
        raise HTTPException(
            status_code=400,
            detail="No readable content found in this PDF. "
                   "Scanned / image-based PDFs are not supported.",
        )
    return _rows_to_df(all_rows)


# ── dispatcher ────────────────────────────────────────────────────────────────

_PDF_MIN_ROWS = 10   # fewer rows than this after text extraction → try OCR


def _read_pdf(content: bytes, password: str = "") -> pd.DataFrame:
    """
    Three-tier PDF extraction cascade:
      1. pdfplumber  — best for most digital bank statements; has OPay-specific path
      2. PyMuPDF     — different text engine, catches what pdfplumber misses
      3. Tesseract OCR — renders each page to an image and reads it pixel-perfect;
                         handles any encoding; slowest but most robust

    Password errors are always propagated immediately (never silently swallowed).
    If a method returns fewer than _PDF_MIN_ROWS rows it is considered a partial
    failure and the next method is tried.
    """
    if not _PDF_AVAILABLE:
        raise HTTPException(
            status_code=400,
            detail="PDF support is not available. Please upload a CSV or Excel file.",
        )

    last_exc: Exception | None = None

    # ── tier 1: pdfplumber ────────────────────────────────────────────────────
    if _PDFPLUMBER_AVAILABLE:
        try:
            df = _read_pdf_pdfplumber(content, password)
            if len(df) >= _PDF_MIN_ROWS:
                return df
        except HTTPException as exc:
            if exc.detail == "PDF_NEEDS_PASSWORD":
                raise
            last_exc = exc
        except Exception as exc:
            last_exc = exc

    # ── tier 2: PyMuPDF ──────────────────────────────────────────────────────
    if _PYMUPDF_AVAILABLE:
        try:
            df = _read_pdf_pymupdf(content, password)
            if len(df) >= _PDF_MIN_ROWS:
                return df
        except HTTPException as exc:
            if exc.detail == "PDF_NEEDS_PASSWORD":
                raise
            last_exc = exc
        except Exception as exc:
            last_exc = exc

    # ── tier 3: Tesseract OCR ─────────────────────────────────────────────────
    if _OCR_AVAILABLE and _PYMUPDF_AVAILABLE:
        return _read_pdf_ocr(content, password)

    # All tiers failed
    raise last_exc or HTTPException(
        status_code=400,
        detail="Could not extract text from this PDF. "
               "Install pytesseract + Tesseract to enable OCR fallback.",
    )


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
