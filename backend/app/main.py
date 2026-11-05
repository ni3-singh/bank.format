"""
FastAPI application for Bank Statement PDF parsing and analysis.
"""

import re
import logging
from datetime import datetime
from typing import Optional

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .analyzer import analyze_transactions
from .bank_formats import (
    clean_description,
    detect_bank_format,
    normalize_dr_cr,
    _normalize_header,
    _find_description_column,
)
from .pdf_parser import extract_tables_from_pdf

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB

app = FastAPI(
    title="Bank Statement Parser API",
    description="Upload bank statement PDFs, extract transactions, and get analytics.",
    version="2.1.0",
)

# CORS – allow all origins for Netlify frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    """API info."""
    return {
        "app": "Bank Statement Parser API",
        "version": "2.1.0",
        "endpoints": {
            "POST /api/parse": "Upload and parse a bank statement PDF",
            "GET /api/health": "Health check",
        },
    }


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.post("/api/parse")
async def parse_statement(file: UploadFile = File(...)):
    """
    Parse a bank statement PDF.

    Accepts a multipart PDF upload, extracts tables, detects the bank format,
    cleans descriptions, normalises into (Date, Name, Dr, Cr, Remark),
    and returns JSON with parsed transactions and analytics.
    """
    # ---- Validate upload ----
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded.")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    contents = await file.read()

    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File size exceeds 25 MB limit.")

    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # ---- Process ----
    try:
        # Step 1: Extract raw tables
        raw_df = extract_tables_from_pdf(contents)

        if raw_df is None or raw_df.empty:
            raise ValueError("No table data could be extracted from the PDF. The PDF may be scanned (image-only) or password protected.")

        logger.info("Raw extracted rows: %d, cols: %d, columns: %s", len(raw_df), raw_df.shape[1], list(raw_df.columns))

        # Step 2: Detect bank format
        bank_format = detect_bank_format(raw_df)
        logger.info("Detected bank format: %s", bank_format)

        # Step 3: Normalise into (Date, Name, Dr, Cr, Remark)
        normalized_df = _normalize_dataframe(raw_df, bank_format)

        if normalized_df.empty:
            raise ValueError("Could not extract any valid transactions. Please check if the statement contains tabular debit/credit entries.")

        logger.info("Normalized transactions: %d", len(normalized_df))

        # Step 4: Analyse
        analytics = analyze_transactions(normalized_df)

        # Step 5: Build response with both lowercase and uppercase keys for total frontend compatibility
        transactions = []
        for _, r in normalized_df.iterrows():
            d_val = str(r["Date"]) if pd.notna(r["Date"]) else ""
            n_val = str(r["Name"]) if pd.notna(r["Name"]) else "UNKNOWN"
            dr_val = round(float(r["Dr"]), 2) if pd.notna(r["Dr"]) else 0.0
            cr_val = round(float(r["Cr"]), 2) if pd.notna(r["Cr"]) else 0.0
            rem_val = str(r["Remark"]) if pd.notna(r["Remark"]) else ""
            transactions.append({
                "date": d_val,
                "name": n_val,
                "dr": dr_val,
                "cr": cr_val,
                "remark": rem_val,
                "Date": d_val,
                "Name": n_val,
                "Dr": dr_val,
                "Cr": cr_val,
                "Remark": rem_val,
            })

        return JSONResponse(content={
            "transactions": transactions,
            "analytics": analytics,
            "bank_detected": bank_format,
            "row_count": len(transactions),
        })

    except ValueError as exc:
        logger.warning("Validation error in parse_statement: %s", str(exc))
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected error in parse_statement: %s", str(exc))
        raise HTTPException(
            status_code=500,
            detail=f"Error processing PDF: {str(exc)}",
        )


# ---------------------------------------------------------------------------
# Normalisation pipeline
# ---------------------------------------------------------------------------

DATE_REGEX = re.compile(
    r"\b(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}|\d{1,2}[\s\-\.](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s\-\.]\d{2,4}|\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2})\b",
    re.IGNORECASE,
)


def _is_amount_cell(val) -> bool:
    """Check if a cell value represents a monetary amount (excluding UTRs, dates, phone numbers)."""
    if val is None:
        return False
    s = str(val).strip()
    if not s or s.lower() in ("", "nan", "none", "null", "-", "--", "nil"):
        return False
    if _is_date_cell(s):
        return False
    s_clean = re.sub(r"[₹$€£,\s]", "", s)
    # Reject long integers (like 10-18 digit UTR/UPI transaction IDs or account numbers)
    if re.match(r"^\d{10,}$", s_clean):
        return False
    # Accept standard decimal or integer amounts
    if re.match(r"^[-+]?\d{1,9}(\.\d{1,2})?$", s_clean):
        try:
            return float(s_clean) > 0
        except ValueError:
            return False
    return False


def _normalize_dataframe(raw_df: pd.DataFrame, bank_format: str) -> pd.DataFrame:
    """
    Map raw extracted columns to the canonical schema:
        Date | Name | Dr | Cr | Remark

    Combines:
    1. Header keyword analysis
    2. Deep content-based cell inspection (Dates, DR/CR markers, numeric amounts, text slashes)
    3. Positional fallbacks for known bank formats (IDBI: D=Desc, G=Dr, H=Cr; Kotak: D=Desc, F=Amt, G=Dr/Cr)
    """
    df = raw_df.copy()
    if df.empty:
        return pd.DataFrame()

    num_rows, num_cols = df.shape
    col_names = list(df.columns)
    col_names_lower = [str(c).strip().lower() for c in col_names]

    # -------------------------------------------------------------
    # Step 1: Detect Date Column
    # -------------------------------------------------------------
    date_col = None
    date_kws = ["txn date", "trans date", "transaction date", "value date", "post date", "posting date", "date"]
    for kw in date_kws:
        for i, h in enumerate(col_names_lower):
            if kw in h:
                date_col = col_names[i]
                break
        if date_col:
            break

    if not date_col:
        # Detect by date frequency across column rows
        date_counts = {}
        for col in col_names:
            cnt = sum(1 for val in df[col].dropna() if _is_date_cell(val))
            date_counts[col] = cnt
        best_col, best_cnt = max(date_counts.items(), key=lambda x: x[1])
        if best_cnt > 0:
            date_col = best_col

    # -------------------------------------------------------------
    # Step 2: Detect Dr/Cr Indicator Column (Kotak style)
    # -------------------------------------------------------------
    indicator_col = None
    indicator_kws = ["dr/cr", "dr / cr", "cr/dr", "txn type", "indicator", "dr_cr"]
    for kw in indicator_kws:
        for i, h in enumerate(col_names_lower):
            if kw in h or h == kw:
                indicator_col = col_names[i]
                break
        if indicator_col:
            break

    if not indicator_col:
        # Check by content: column where majority of entries are DR / CR
        for col in col_names:
            if col == date_col:
                continue
            vals = [str(v).strip().upper() for v in df[col].dropna() if str(v).strip()]
            if not vals:
                continue
            drcr_cnt = sum(1 for v in vals if v in ("DR", "CR", "D", "C", "DR.", "CR."))
            if (drcr_cnt / len(vals)) >= 0.20:
                indicator_col = col
                break

    # -------------------------------------------------------------
    # Step 3: Detect Description Column
    # -------------------------------------------------------------
    desc_col = None
    desc_kws = ["description", "narration", "particulars", "details", "remark", "remarks", "transaction details"]
    for kw in desc_kws:
        for i, h in enumerate(col_names_lower):
            if kw in h:
                desc_col = col_names[i]
                break
        if desc_col:
            break

    if not desc_col:
        # Score columns by text length, presence of slashes / hyphens, and transaction keywords
        scores = {}
        for col in col_names:
            if col in (date_col, indicator_col):
                continue
            str_vals = [str(v).strip() for v in df[col].dropna() if str(v).strip()]
            if not str_vals:
                continue
            avg_len = sum(len(v) for v in str_vals) / len(str_vals)
            slash_cnt = sum(v.count("/") for v in str_vals)
            hyphen_cnt = sum(v.count("-") for v in str_vals)
            score = avg_len + (slash_cnt * 6) + (hyphen_cnt * 2)
            scores[col] = score
        if scores:
            desc_col = max(scores.items(), key=lambda x: x[1])[0]

    # -------------------------------------------------------------
    # Step 4: Detect Amount Columns (Debit, Credit, or Single Amount)
    # -------------------------------------------------------------
    dr_col = None
    cr_col = None
    amount_col = None

    if indicator_col:
        bank_format = "kotak"
        # Look for amount column in header
        amt_kws = ["amount", "txn amount", "transaction amount", "amt"]
        for kw in amt_kws:
            for i, h in enumerate(col_names_lower):
                if kw in h and col_names[i] not in (date_col, desc_col, indicator_col):
                    amount_col = col_names[i]
                    break
            if amount_col:
                break

        if not amount_col:
            num_counts = {}
            for col in col_names:
                if col in (date_col, desc_col, indicator_col):
                    continue
                cnt = sum(1 for v in df[col].dropna() if _is_amount_cell(v))
                num_counts[col] = cnt
            if num_counts:
                amount_col = max(num_counts.items(), key=lambda x: x[1])[0]
    else:
        dr_kws = ["debit", "withdrawal", "withdrawals", "dr", "debit amount", "debit amt", "paid out"]
        cr_kws = ["credit", "deposit", "deposits", "cr", "credit amount", "credit amt", "paid in"]

        for kw in dr_kws:
            for i, h in enumerate(col_names_lower):
                if kw in h and col_names[i] not in (date_col, desc_col):
                    dr_col = col_names[i]
                    break
            if dr_col:
                break

        for kw in cr_kws:
            for i, h in enumerate(col_names_lower):
                if kw in h and col_names[i] not in (date_col, desc_col, dr_col):
                    cr_col = col_names[i]
                    break
            if cr_col:
                break

        # If headers did not match, detect numeric columns by content
        if not dr_col or not cr_col:
            numeric_cols = []
            for col in col_names:
                if col in (date_col, desc_col, indicator_col):
                    continue
                cnt = sum(1 for v in df[col].dropna() if _is_amount_cell(v))
                if cnt >= max(1, len(df) * 0.05):
                    numeric_cols.append(col)

            if len(numeric_cols) >= 2:
                # Debit/Withdrawal comes first, Credit/Deposit comes second
                dr_col = numeric_cols[0]
                cr_col = numeric_cols[1]
            elif len(numeric_cols) == 1:
                amount_col = numeric_cols[0]

    # Positional heuristics fallback (e.g. user's Colab output)
    if not desc_col and len(col_names) > 3:
        desc_col = col_names[3]
    if not dr_col and not amount_col:
        if len(col_names) > 7:
            dr_col = col_names[6]
            cr_col = col_names[7]
        elif len(col_names) > 5:
            amount_col = col_names[5]

    logger.info("Mapped columns: date=%s, desc=%s, dr=%s, cr=%s, indicator=%s, amount=%s",
                date_col, desc_col, dr_col, cr_col, indicator_col, amount_col)

    # -------------------------------------------------------------
    # Step 5: Normalize Rows
    # -------------------------------------------------------------
    records = []
    for _, row in df.iterrows():
        raw_date = str(row.get(date_col, "")).strip() if date_col else ""
        parsed_date = _parse_date(raw_date)

        raw_desc = str(row.get(desc_col, "")).strip() if desc_col else ""

        # Amounts
        if indicator_col and amount_col:
            amt = _parse_amount_safe(row.get(amount_col))
            ind = str(row.get(indicator_col, "")).strip().upper()
            if "DR" in ind or ind == "D":
                dr_val, cr_val = amt, 0.0
            elif "CR" in ind or ind == "C":
                dr_val, cr_val = 0.0, amt
            else:
                dr_val, cr_val = amt, 0.0
        elif dr_col or cr_col:
            dr_val = _parse_amount_safe(row.get(dr_col)) if dr_col else 0.0
            cr_val = _parse_amount_safe(row.get(cr_col)) if cr_col else 0.0
        elif amount_col:
            amt = _parse_amount_safe(row.get(amount_col))
            dr_val, cr_val = amt, 0.0
        else:
            dr_val, cr_val = 0.0, 0.0

        # Skip rows where Dr, Cr, and parsed_date are all missing
        if dr_val == 0.0 and cr_val == 0.0 and not parsed_date:
            continue

        # Skip summary / banner rows
        row_str = " ".join(str(v) for v in row.values).lower()
        if any(term in row_str for term in [
            "opening balance", "closing balance", "total", "page total",
            "brought forward", "carried forward", "grand total",
            "statement of account", "account details"
        ]):
            if dr_val == 0.0 and cr_val == 0.0:
                continue

        # Clean name from description
        name = clean_description(raw_desc, bank_format)

        records.append({
            "Date": parsed_date or raw_date,
            "Name": name,
            "Dr": round(dr_val, 2),
            "Cr": round(cr_val, 2),
            "Remark": raw_desc,
        })

    return pd.DataFrame(records)


def _parse_amount_safe(value) -> float:
    """Parse amount, returning 0.0 on failure."""
    if value is None:
        return 0.0
    s = str(value).strip()
    if not s or s.lower() in ("", "nan", "none", "null", "-", "--", "nil"):
        return 0.0
    s = re.sub(r"[₹$€£,\s]", "", s)

    # Handle parenthetical negatives: (1234.56) -> 1234.56
    match_paren = re.match(r"^\(([0-9.]+)\)$", s)
    if match_paren:
        return abs(float(match_paren.group(1)))

    match = re.search(r"[-+]?\d*\.?\d+", s)
    if match:
        try:
            return abs(float(match.group()))
        except (ValueError, TypeError):
            return 0.0
    return 0.0


def _parse_date(raw: str) -> str:
    """Parse various date formats into DD-MM-YYYY."""
    if not raw or raw.lower() in ("nan", "none", "null", "", "-"):
        return ""

    raw = raw.strip()
    raw = re.sub(r"^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+", "", raw, flags=re.IGNORECASE)

    # Extract matching date substring if wrapped with time or text
    m = DATE_REGEX.search(raw)
    if m:
        raw = m.group(1).strip()

    formats = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d %b %Y",
        "%d-%b-%Y",
        "%d/%b/%Y",
        "%Y-%m-%d",
        "%d/%m/%y",
        "%d-%m-%y",
        "%d %b %y",
        "%d-%b-%y",
        "%m/%d/%Y",
        "%Y/%m/%d",
        "%d.%m.%Y",
        "%d.%m.%y",
        "%d %B %Y",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.strftime("%d-%m-%Y")
        except ValueError:
            continue

    try:
        dt = pd.to_datetime(raw, dayfirst=True)
        if pd.notna(dt):
            return dt.strftime("%d-%m-%Y")
    except Exception:
        pass

    return raw
