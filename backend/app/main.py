"""
FastAPI application: PDF to Excel and CSV Converter for Bank Statements.
"""

import io
import re
import logging
from datetime import datetime
from typing import Optional, List

import pandas as pd
import pdfplumber
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

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

MAX_FILE_SIZE = 30 * 1024 * 1024  # 30 MB

app = FastAPI(
    title="PDF to Excel & CSV Converter",
    description="Convert bank statement PDFs into Excel (.xlsx) and CSV (.csv) files. Zero data retention.",
    version="2.2.0",
)

# CORS – allow all origins for Netlify frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _col_letter(col_idx: int) -> str:
    """Convert 0-based column index to Excel column letter (0->A, 25->Z, 26->AA)."""
    result = ""
    col_idx += 1
    while col_idx > 0:
        col_idx, remainder = divmod(col_idx - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _extract_tables_colab_style(pdf_bytes: bytes) -> tuple:
    """
    Extract all tables across pages using the exact approach from Google Colab.
    Returns (final_df, page_count).
    """
    all_tables = []
    page_count = 0

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        page_count = len(pdf.pages)
        for page in pdf.pages:
            tables = page.extract_tables()
            if not tables:
                # Text fallback for borderless PDFs
                tables = page.extract_tables(table_settings={
                    "vertical_strategy": "text",
                    "horizontal_strategy": "text",
                    "snap_tolerance": 5,
                    "join_tolerance": 5,
                })

            for table in (tables or []):
                if table:
                    clean_table = [
                        [("" if cell is None else str(cell).replace("\r", " ").replace("\n", " ").strip()) for cell in row]
                        for row in table
                        if any(c is not None and str(c).strip() != "" for c in row)
                    ]
                    if clean_table:
                        df = pd.DataFrame(clean_table)
                        all_tables.append(df)

    if not all_tables:
        raise ValueError("No table data could be detected in the PDF. Please check if the PDF is an image scan or password-protected.")

    # Harmonize columns across tables
    max_cols = max(df.shape[1] for df in all_tables)
    aligned_dfs = []
    for df in all_tables:
        if df.shape[1] < max_cols:
            for i in range(df.shape[1], max_cols):
                df[i] = ""
        elif df.shape[1] > max_cols:
            df = df.iloc[:, :max_cols]
        # Rename columns to standard 0..max_cols-1 integers
        df.columns = list(range(max_cols))
        aligned_dfs.append(df)

    final_df = pd.concat(aligned_dfs, ignore_index=True)
    return final_df, page_count


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    """API info."""
    return {
        "app": "PDF to Excel & CSV Converter",
        "version": "2.2.0",
        "endpoints": {
            "POST /api/convert": "Upload PDF, extract all tables, return preview + download data",
            "POST /api/download/excel": "Upload PDF, get converted Excel (.xlsx) file directly",
            "POST /api/download/csv": "Upload PDF, get converted CSV (.csv) file directly",
            "POST /api/parse": "Upload PDF, get parsed transactions and bank analytics",
            "GET /api/health": "Health check",
        },
    }


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.post("/api/convert")
async def convert_pdf(file: UploadFile = File(...)):
    """
    Convert bank statement PDF into Excel/CSV table data.
    Runs the exact Google Colab extraction logic: extracts all tables,
    concatenates into one DataFrame, and prepares both raw and cleaned data.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded.")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File size exceeds 30 MB limit.")
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        final_df, page_count = _extract_tables_colab_style(contents)

        num_rows, num_cols = final_df.shape
        excel_headers = [_col_letter(i) for i in range(num_cols)]

        # Raw rows for frontend table preview
        rows = final_df.values.tolist()

        # Optional: Try to run cleaned bank summary if format matches
        cleaned_summary = None
        try:
            bank_format = detect_bank_format(final_df)
            norm_df = _normalize_dataframe(final_df, bank_format)
            if not norm_df.empty:
                analytics = analyze_transactions(norm_df)
                txs = []
                for _, r in norm_df.iterrows():
                    d_val = str(r["Date"]) if pd.notna(r["Date"]) else ""
                    n_val = str(r["Name"]) if pd.notna(r["Name"]) else "UNKNOWN"
                    dr_val = round(float(r["Dr"]), 2) if pd.notna(r["Dr"]) else 0.0
                    cr_val = round(float(r["Cr"]), 2) if pd.notna(r["Cr"]) else 0.0
                    rem_val = str(r["Remark"]) if pd.notna(r["Remark"]) else ""
                    txs.append({
                        "date": d_val, "name": n_val, "dr": dr_val, "cr": cr_val, "remark": rem_val,
                        "Date": d_val, "Name": n_val, "Dr": dr_val, "Cr": cr_val, "Remark": rem_val,
                    })
                cleaned_summary = {
                    "bank_detected": bank_format,
                    "transactions": txs,
                    "analytics": analytics,
                }
        except Exception as e:
            logger.info("Bank summary could not be extracted (will show raw table): %s", str(e))

        return JSONResponse(content={
            "filename": file.filename,
            "total_pages": page_count,
            "total_rows": num_rows,
            "total_cols": num_cols,
            "headers": excel_headers,
            "rows": rows[:1000],  # preview up to 1000 rows
            "cleaned_summary": cleaned_summary,
            # Backward-compatible fields
            "transactions": cleaned_summary["transactions"] if cleaned_summary else [],
            "analytics": cleaned_summary["analytics"] if cleaned_summary else None,
            "bank_detected": cleaned_summary["bank_detected"] if cleaned_summary else "generic",
        })

    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.exception("Error converting PDF: %s", str(exc))
        raise HTTPException(status_code=500, detail=f"Error converting PDF: {str(exc)}")


@app.post("/api/download/excel")
async def download_excel_file(file: UploadFile = File(...)):
    """Stream converted Excel file directly to browser."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    contents = await file.read()
    final_df, _ = _extract_tables_colab_style(contents)

    excel_buf = io.BytesIO()
    final_df.to_excel(excel_buf, index=False, header=False, engine="openpyxl")
    excel_buf.seek(0)

    base_name = file.filename.rsplit(".", 1)[0]
    return StreamingResponse(
        excel_buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{base_name}.xlsx"'},
    )


@app.post("/api/download/csv")
async def download_csv_file(file: UploadFile = File(...)):
    """Stream converted CSV file directly to browser."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    contents = await file.read()
    final_df, _ = _extract_tables_colab_style(contents)

    csv_buf = io.StringIO()
    final_df.to_csv(csv_buf, index=False, header=False)
    csv_bytes = io.BytesIO(csv_buf.getvalue().encode("utf-8-sig"))

    base_name = file.filename.rsplit(".", 1)[0]
    return StreamingResponse(
        csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{base_name}.csv"'},
    )


@app.post("/api/parse")
async def parse_statement(file: UploadFile = File(...)):
    """Legacy endpoint redirecting to convert_pdf."""
    return await convert_pdf(file)


# ---------------------------------------------------------------------------
# Normalisation pipeline
# ---------------------------------------------------------------------------

DATE_REGEX = re.compile(
    r"\b(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}|\d{1,2}[\s\-\.](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s\-\.]\d{2,4}|\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2})\b",
    re.IGNORECASE,
)


def _is_date_cell(val) -> bool:
    if not val:
        return False
    return bool(DATE_REGEX.search(str(val).strip()))


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
    if re.match(r"^\d{10,}$", s_clean):
        return False
    if re.match(r"^[-+]?\d{1,9}(\.\d{1,2})?$", s_clean):
        try:
            return float(s_clean) > 0
        except ValueError:
            return False
    return False


def _normalize_dataframe(raw_df: pd.DataFrame, bank_format: str) -> pd.DataFrame:
    """Map raw extracted columns to canonical schema: Date | Name | Dr | Cr | Remark."""
    df = raw_df.copy()
    if df.empty:
        return pd.DataFrame()

    num_rows, num_cols = df.shape
    col_names = list(df.columns)
    col_names_lower = [str(c).strip().lower() for c in col_names]

    # Date
    date_col = None
    date_kws = ["txn date", "trans date", "transaction date", "value date", "post date", "posting date", "date"]
    for kw in date_kws:
        for i, h in enumerate(col_names_lower):
            if kw in h:
                date_col = col_names[i]
                break
        if date_col is not None:
            break

    if date_col is None:
        date_counts = {col: sum(1 for val in df[col].dropna() if _is_date_cell(val)) for col in col_names}
        best_col, best_cnt = max(date_counts.items(), key=lambda x: x[1])
        if best_cnt > 0:
            date_col = best_col

    # Indicator (Kotak)
    indicator_col = None
    indicator_kws = ["dr/cr", "dr / cr", "cr/dr", "txn type", "indicator", "dr_cr"]
    for kw in indicator_kws:
        for i, h in enumerate(col_names_lower):
            if kw in h or h == kw:
                indicator_col = col_names[i]
                break
        if indicator_col is not None:
            break

    if indicator_col is None:
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

    # Description
    desc_col = None
    desc_kws = ["description", "narration", "particulars", "details", "remark", "remarks", "transaction details"]
    for kw in desc_kws:
        for i, h in enumerate(col_names_lower):
            if kw in h:
                desc_col = col_names[i]
                break
        if desc_col is not None:
            break

    if desc_col is None:
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
            scores[col] = avg_len + (slash_cnt * 6) + (hyphen_cnt * 2)
        if scores:
            desc_col = max(scores.items(), key=lambda x: x[1])[0]

    # Amounts
    dr_col = None
    cr_col = None
    amount_col = None

    if indicator_col is not None:
        bank_format = "kotak"
        amt_kws = ["amount", "txn amount", "transaction amount", "amt"]
        for kw in amt_kws:
            for i, h in enumerate(col_names_lower):
                if kw in h and col_names[i] not in (date_col, desc_col, indicator_col):
                    amount_col = col_names[i]
                    break
            if amount_col is not None:
                break

        if amount_col is None:
            num_counts = {
                col: sum(1 for v in df[col].dropna() if _is_amount_cell(v))
                for col in col_names if col not in (date_col, desc_col, indicator_col)
            }
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
            if dr_col is not None:
                break

        for kw in cr_kws:
            for i, h in enumerate(col_names_lower):
                if kw in h and col_names[i] not in (date_col, desc_col, dr_col):
                    cr_col = col_names[i]
                    break
            if cr_col is not None:
                break

        if dr_col is None or cr_col is None:
            numeric_cols = [
                col for col in col_names
                if col not in (date_col, desc_col, indicator_col)
                and sum(1 for v in df[col].dropna() if _is_amount_cell(v)) >= max(1, len(df) * 0.05)
            ]
            if len(numeric_cols) >= 2:
                dr_col = numeric_cols[0]
                cr_col = numeric_cols[1]
            elif len(numeric_cols) == 1:
                amount_col = numeric_cols[0]

    # Positional heuristics fallback
    if desc_col is None and len(col_names) > 3:
        desc_col = col_names[3]
    if dr_col is None and amount_col is None:
        if len(col_names) > 7:
            dr_col = col_names[6]
            cr_col = col_names[7]
        elif len(col_names) > 5:
            amount_col = col_names[5]

    # Normalize Rows
    records = []
    for _, row in df.iterrows():
        raw_date = str(row.get(date_col, "")).strip() if date_col is not None else ""
        parsed_date = _parse_date(raw_date)
        raw_desc = str(row.get(desc_col, "")).strip() if desc_col is not None else ""

        if indicator_col is not None and amount_col is not None:
            amt = _parse_amount_safe(row.get(amount_col))
            ind = str(row.get(indicator_col, "")).strip().upper()
            if "DR" in ind or ind == "D":
                dr_val, cr_val = amt, 0.0
            elif "CR" in ind or ind == "C":
                dr_val, cr_val = 0.0, amt
            else:
                dr_val, cr_val = amt, 0.0
        elif dr_col is not None or cr_col is not None:
            dr_val = _parse_amount_safe(row.get(dr_col)) if dr_col is not None else 0.0
            cr_val = _parse_amount_safe(row.get(cr_col)) if cr_col is not None else 0.0
        elif amount_col is not None:
            amt = _parse_amount_safe(row.get(amount_col))
            dr_val, cr_val = amt, 0.0
        else:
            dr_val, cr_val = 0.0, 0.0

        if dr_val == 0.0 and cr_val == 0.0 and not parsed_date:
            continue

        row_str = " ".join(str(v) for v in row.values).lower()
        if any(term in row_str for term in [
            "opening balance", "closing balance", "total", "page total",
            "brought forward", "carried forward", "grand total",
            "statement of account", "account details"
        ]):
            if dr_val == 0.0 and cr_val == 0.0:
                continue

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
    if value is None:
        return 0.0
    s = str(value).strip()
    if not s or s.lower() in ("", "nan", "none", "null", "-", "--", "nil"):
        return 0.0
    s = re.sub(r"[₹$€£,\s]", "", s)
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
    if not raw or raw.lower() in ("nan", "none", "null", "", "-"):
        return ""
    raw = raw.strip()
    raw = re.sub(r"^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+", "", raw, flags=re.IGNORECASE)
    m = DATE_REGEX.search(raw)
    if m:
        raw = m.group(1).strip()
    formats = [
        "%d/%m/%Y", "%d-%m-%Y", "%d %b %Y", "%d-%b-%Y", "%d/%b/%Y",
        "%Y-%m-%d", "%d/%m/%y", "%d-%m-%y", "%d %b %y", "%d-%b-%y",
        "%m/%d/%Y", "%Y/%m/%d", "%d.%m.%Y", "%d.%m.%y", "%d %B %Y",
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
