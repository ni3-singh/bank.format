"""
PDF table extraction using pdfplumber.

Handles messy bank PDFs: merged cells, empty rows, multi-row headers,
borderless tables, multi-page statements, etc.
"""

import io
import re
from typing import List, Optional

import pandas as pd
import pdfplumber

HEADER_KEYWORDS = [
    "date", "txn date", "transaction date", "trans date", "trans. date",
    "value date", "post date", "posting date",
    "description", "narration", "particulars", "details", "remark", "remarks",
    "transaction details", "transaction particulars",
    "debit", "withdrawal", "withdrawals", "dr", "debit amount", "debit amt",
    "withdrawal amt", "withdrawal amt.",
    "credit", "deposit", "deposits", "cr", "credit amount", "credit amt",
    "deposit amt", "deposit amt.",
    "amount", "txn amount", "transaction amount",
    "balance", "closing balance", "running balance",
    "dr/cr", "dr / cr", "type", "txn type", "cr/dr",
    "chq", "cheque", "chq no", "cheque no", "ref", "ref no", "reference",
    "sl no", "sr no", "s.no", "sl.no",
]


def extract_tables_from_pdf(pdf_bytes: bytes) -> pd.DataFrame:
    """
    Extract all transaction tables from a bank statement PDF.

    Uses multiple extraction strategies:
    1. Default extraction (identical to Google Colab: page.extract_tables())
    2. Text strategy (for borderless statements)
    3. Lines strategy (for bordered statements)
    4. Word-coordinate clustering fallback
    """
    candidate_tables: List[List[List[str]]] = []

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            tables = []

            # Strategy 1: Default extraction (same as Google Colab)
            try:
                tables = page.extract_tables()
            except Exception:
                tables = []

            # Strategy 2: Text-based strategy if default returned nothing
            if not tables or not any(len(t) > 1 for t in tables):
                try:
                    tables = page.extract_tables(table_settings={
                        "vertical_strategy": "text",
                        "horizontal_strategy": "text",
                        "snap_tolerance": 5,
                        "join_tolerance": 5,
                    })
                except Exception:
                    tables = []

            # Strategy 3: Line-based strategy
            if not tables or not any(len(t) > 1 for t in tables):
                try:
                    tables = page.extract_tables(table_settings={
                        "vertical_strategy": "lines",
                        "horizontal_strategy": "lines",
                        "snap_tolerance": 5,
                        "join_tolerance": 5,
                    })
                except Exception:
                    tables = []

            # Clean each table
            page_clean_tables = []
            for t in (tables or []):
                if not t:
                    continue
                clean_t = []
                for row in t:
                    if row is None:
                        continue
                    clean_row = [_clean_cell(c) for c in row]
                    if any(c != "" for c in clean_row):
                        clean_t.append(clean_row)
                if clean_t and len(clean_t) >= 1:
                    page_clean_tables.append(clean_t)

            # Strategy 4: Fallback to coordinate-based word clustering
            if not page_clean_tables:
                words_table = _extract_words_as_table(page)
                if words_table:
                    page_clean_tables.append(words_table)

            candidate_tables.extend(page_clean_tables)

    if not candidate_tables:
        raise ValueError("No table data could be detected in the PDF.")

    # Find the maximum column count across all extracted tables
    max_cols = max(len(t[0]) for t in candidate_tables if t)

    # Filter tables: keep transaction tables (ignore small 1-2 column summary boxes)
    min_cols = max(3, max_cols - 2) if max_cols >= 4 else 2
    tx_tables = [t for t in candidate_tables if len(t[0]) >= min_cols]

    if not tx_tables:
        tx_tables = candidate_tables

    target_cols = max(len(t[0]) for t in tx_tables)

    # Flatten and normalize column count
    all_rows: List[List[str]] = []
    for t in tx_tables:
        for row in t:
            if len(row) < target_cols:
                row = row + [""] * (target_cols - len(row))
            elif len(row) > target_cols:
                row = row[:target_cols]
            all_rows.append(row)

    if not all_rows:
        raise ValueError("No rows found in extracted tables.")

    # Find header row in the top 20 rows
    header_idx = _find_header_row_index(all_rows[:20])

    if header_idx is not None:
        header_row = all_rows[header_idx]
        data_rows = all_rows[header_idx + 1:]
        header = [_clean_cell(c) or f"Col_{i}" for i, c in enumerate(header_row)]
        header = _deduplicate_columns(header)

        # Drop duplicate header rows that repeat on subsequent pages
        header_lower = [h.lower().strip() for h in header]
        filtered_rows = []
        for r in data_rows:
            r_lower = [str(c).lower().strip() for c in r]
            if r_lower == header_lower:
                continue
            filtered_rows.append(r)

        df = pd.DataFrame(filtered_rows, columns=header)
    else:
        # No explicit header detected: use generic column names
        header = [f"Col_{i}" for i in range(target_cols)]
        df = pd.DataFrame(all_rows, columns=header)

    return df


def _clean_cell(cell) -> str:
    """Clean a single cell value from PDF extraction."""
    if cell is None:
        return ""
    s = str(cell)
    s = re.sub(r"[\r\n\x0a\x0d]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _find_header_row_index(rows: List[List[str]]) -> Optional[int]:
    """Find the row that looks most like a table header."""
    for idx, row in enumerate(rows):
        matches = 0
        for cell in row:
            if not cell:
                continue
            c_clean = re.sub(r"[^a-z/ ]", "", str(cell).lower().strip())
            for kw in HEADER_KEYWORDS:
                if kw in c_clean:
                    matches += 1
                    break
        if matches >= 2:
            return idx
    return None


def _deduplicate_columns(columns: list) -> list:
    """Ensure column names are unique."""
    seen = {}
    result = []
    for col in columns:
        name = str(col).strip() if col else "Column"
        if not name:
            name = "Column"
        if name in seen:
            seen[name] += 1
            result.append(f"{name}_{seen[name]}")
        else:
            seen[name] = 0
            result.append(name)
    return result


def _extract_words_as_table(page) -> List[List[str]]:
    """Fallback: cluster words into rows by y-coordinate."""
    try:
        words = page.extract_words(x_tolerance=3, y_tolerance=3)
        if not words:
            return []

        # Sort by top coordinate then x0
        words.sort(key=lambda w: (w["top"], w["x0"]))

        lines = []
        current_line = []
        current_top = None

        for w in words:
            if current_top is None or abs(w["top"] - current_top) <= 4:
                current_line.append(w)
                current_top = w["top"]
            else:
                if current_line:
                    lines.append(current_line)
                current_line = [w]
                current_top = w["top"]
        if current_line:
            lines.append(current_line)

        rows = []
        for line in lines:
            line.sort(key=lambda w: w["x0"])
            row_cells = []
            cur_cell = []
            last_x1 = None
            for w in line:
                if last_x1 is None or (w["x0"] - last_x1) < 14:
                    cur_cell.append(w["text"])
                else:
                    row_cells.append(" ".join(cur_cell))
                    cur_cell = [w["text"]]
                last_x1 = w["x1"]
            if cur_cell:
                row_cells.append(" ".join(cur_cell))
            if row_cells:
                rows.append(row_cells)
        return rows
    except Exception:
        return []
