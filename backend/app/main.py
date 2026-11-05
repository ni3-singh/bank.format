"""
FastAPI application for Bank Statement PDF parsing and analysis.
"""

import re
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

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

app = FastAPI(
    title="Bank Statement Parser API",
    description="Upload bank statement PDFs, extract transactions, and get analytics.",
    version="2.0.0",
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
        "version": "2.0.0",
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
        raise HTTPException(status_code=413, detail="File size exceeds 10 MB limit.")

    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # ---- Process ----
    try:
        # Step 1: Extract raw tables
        raw_df = extract_tables_from_pdf(contents)

        if raw_df.empty:
            raise ValueError("No data rows found in the PDF.")

        # Step 2: Detect bank format
        bank_format = detect_bank_format(raw_df)

        # Step 3: Normalise into (Date, Name, Dr, Cr, Remark)
        normalized_df = _normalize_dataframe(raw_df, bank_format)

        if normalized_df.empty:
            raise ValueError("Could not normalise any transactions from the PDF.")

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
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing PDF: {str(exc)}",
        )


# ---------------------------------------------------------------------------
# Normalisation pipeline
# ---------------------------------------------------------------------------

# Date column keywords (in order of preference)
_DATE_KEYWORDS = [
    "date", "txn date", "transaction date", "trans date", "trans. date",
    "value date", "posting date", "post date",
]

# Description column keywords
_DESC_KEYWORDS = [
    "description", "narration", "particulars", "details",
    "transaction details", "transaction particulars",
]

# Debit column keywords
_DR_KEYWORDS = [
    "debit", "withdrawal", "withdrawal amt.", "withdrawal amt",
    "dr", "debit amount", "debit amt",
]

# Credit column keywords
_CR_KEYWORDS = [
    "credit", "deposit", "deposit amt.", "deposit amt",
    "cr", "credit amount", "credit amt",
]

# Amount column keywords (for banks with a single amount column)
_AMOUNT_KEYWORDS = ["amount", "txn amount", "transaction amount"]

# DR/CR indicator column keywords
_INDICATOR_KEYWORDS = ["dr/cr", "dr / cr", "type", "txn type", "dr/cr indicator"]


def _find_column(df, keywords: list) -> Optional[str]:
    """Find a column whose normalised name matches one of the keywords."""
    for kw in keywords:
        for col in df.columns:
            norm = _normalize_header(col)
            if norm == kw or kw in norm:
                return col
    return None


def _normalize_dataframe(raw_df: pd.DataFrame, bank_format: str) -> pd.DataFrame:
    """
    Map raw extracted columns to the canonical schema:
        Date | Name | Dr | Cr | Remark

    Handles both separate and combined DR/CR columns.
    """
    df = raw_df.copy()

    # --- Identify key columns ---
    date_col = _find_column(df, _DATE_KEYWORDS)
    desc_col = _find_description_column(df)
    dr_col = _find_column(df, _DR_KEYWORDS)
    cr_col = _find_column(df, _CR_KEYWORDS)
    amount_col = _find_column(df, _AMOUNT_KEYWORDS)
    indicator_col = _find_column(df, _INDICATOR_KEYWORDS)

    # For Kotak-style: single amount + indicator
    if bank_format == "kotak" and amount_col is None and dr_col is not None and indicator_col is not None:
        amount_col = dr_col
        dr_col = None

    # If we still don't have dr/cr columns, try amount + indicator
    if dr_col is None and cr_col is None and amount_col and indicator_col:
        bank_format = "kotak"  # treat as single-amount with indicator

    # Build normalised rows
    records = []
    for _, row in df.iterrows():
        # --- Date ---
        raw_date = str(row.get(date_col, "")).strip() if date_col else ""
        parsed_date = _parse_date(raw_date)

        # Skip rows without a valid date (likely sub-headers, footers, totals)
        if not parsed_date:
            # Check if row has any amount – might still be valid with missing date
            has_amount = False
            if dr_col and _parse_amount_safe(row.get(dr_col)) > 0:
                has_amount = True
            if cr_col and _parse_amount_safe(row.get(cr_col)) > 0:
                has_amount = True
            if amount_col and _parse_amount_safe(row.get(amount_col)) > 0:
                has_amount = True
            if not has_amount:
                continue
            parsed_date = ""

        # --- Description / Name ---
        raw_desc = str(row.get(desc_col, "")).strip() if desc_col else ""
        name = clean_description(raw_desc, bank_format)

        # --- Dr / Cr ---
        row_dict = row.to_dict()
        dr_val, cr_val = normalize_dr_cr(
            row_dict,
            bank_format,
            amount_col=amount_col,
            dr_col=dr_col,
            cr_col=cr_col,
            indicator_col=indicator_col,
        )

        # Skip rows where both Dr and Cr are zero (summary / info rows)
        if dr_val == 0.0 and cr_val == 0.0:
            continue

        records.append({
            "Date": parsed_date,
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
    if not s or s.lower() in ("", "nan", "none", "null", "-", "--"):
        return 0.0
    s = re.sub(r"[₹$€£,\s]", "", s)
    try:
        return abs(float(s))
    except (ValueError, TypeError):
        return 0.0


def _parse_date(raw: str) -> str:
    """
    Parse various date formats into DD-MM-YYYY.

    Supported inputs:
        DD/MM/YYYY, DD-MM-YYYY, DD MMM YYYY, YYYY-MM-DD,
        DD/MM/YY, DD-MM-YY, D/M/YYYY, etc.

    Returns empty string if unparseable.
    """
    if not raw or raw.lower() in ("nan", "none", "null", "", "-"):
        return ""

    raw = raw.strip()

    # Remove day-of-week prefixes like "Mon ", "Tue 01/01/2024"
    raw = re.sub(r"^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+", "", raw, flags=re.IGNORECASE)

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

    # Last resort: pandas
    try:
        dt = pd.to_datetime(raw, dayfirst=True)
        if pd.notna(dt):
            return dt.strftime("%d-%m-%Y")
    except Exception:
        pass

    return ""
