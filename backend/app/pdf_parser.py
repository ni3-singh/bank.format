"""
PDF table extraction using pdfplumber.

Handles messy bank PDFs: merged cells, empty rows, multi-row headers, etc.
"""

import io
import re
from typing import List, Optional

import pandas as pd
import pdfplumber


def extract_tables_from_pdf(pdf_bytes: bytes) -> pd.DataFrame:
    """
    Extract all tables from a PDF and concatenate into a single DataFrame.

    Args:
        pdf_bytes: Raw PDF file bytes.

    Returns:
        A single pandas DataFrame with all extracted rows.

    Raises:
        ValueError: If no tables can be extracted.
    """
    all_rows: List[list] = []
    header: Optional[list] = None

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page_num, page in enumerate(pdf.pages):
            tables = page.extract_tables(
                table_settings={
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "lines",
                    "snap_tolerance": 5,
                    "join_tolerance": 5,
                    "edge_min_length": 10,
                    "min_words_vertical": 1,
                    "min_words_horizontal": 1,
                    "text_x_tolerance": 3,
                    "text_y_tolerance": 3,
                }
            )

            if not tables:
                # Retry with text strategy if lines-based extraction fails
                tables = page.extract_tables(
                    table_settings={
                        "vertical_strategy": "text",
                        "horizontal_strategy": "text",
                        "snap_tolerance": 5,
                        "join_tolerance": 5,
                    }
                )

            for table in tables:
                if not table:
                    continue

                for row_idx, row in enumerate(table):
                    if row is None:
                        continue

                    # Clean each cell
                    cleaned_row = [_clean_cell(cell) for cell in row]

                    # Skip completely empty rows
                    if all(c == "" or c is None for c in cleaned_row):
                        continue

                    # Detect header row
                    if header is None and _is_header_row(cleaned_row):
                        header = cleaned_row
                        continue

                    all_rows.append(cleaned_row)

    if not all_rows:
        raise ValueError("No table data could be extracted from the PDF.")

    # Build DataFrame
    if header:
        # Ensure all rows have the same number of columns as header
        num_cols = len(header)
        normalized_rows = []
        for row in all_rows:
            if len(row) < num_cols:
                row = row + [""] * (num_cols - len(row))
            elif len(row) > num_cols:
                row = row[:num_cols]
            normalized_rows.append(row)

        # Handle duplicate column names
        header = _deduplicate_columns(header)
        df = pd.DataFrame(normalized_rows, columns=header)
    else:
        df = pd.DataFrame(all_rows)
        # Try to use the first row as header if it looks like one
        if len(df) > 1 and _is_header_row(df.iloc[0].tolist()):
            new_header = [_clean_cell(c) for c in df.iloc[0].tolist()]
            new_header = _deduplicate_columns(new_header)
            df = df.iloc[1:].reset_index(drop=True)
            df.columns = new_header

    # Drop rows that are duplicates of the header (headers repeated on each page)
    if header:
        header_lower = [str(h).lower().strip() for h in header]
        mask = df.apply(
            lambda row: [str(v).lower().strip() for v in row.tolist()] != header_lower,
            axis=1,
        )
        df = df[mask].reset_index(drop=True)

    return df


def _clean_cell(cell) -> str:
    """Clean a single cell value from PDF extraction."""
    if cell is None:
        return ""
    s = str(cell)
    # Replace embedded newlines with space
    s = re.sub(r"[\r\n\x0a\x0d]+", " ", s)
    # Collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _is_header_row(row: list) -> bool:
    """
    Check if a row looks like a table header.

    Looks for date-related keywords, financial column names, etc.
    """
    header_keywords = {
        "date", "txn date", "transaction date", "value date", "posting date",
        "description", "narration", "particulars", "details", "remark", "remarks",
        "debit", "credit", "withdrawal", "deposit", "amount",
        "balance", "closing balance", "running balance",
        "dr", "cr", "dr/cr", "dr / cr",
        "ref", "reference", "chq", "cheque", "ref no", "chq no",
        "sl", "sl no", "sr", "sr no", "s.no", "sl.no",
        "withdrawal amt.", "deposit amt.", "closing balance",
    }

    matches = 0
    for cell in row:
        if cell is None:
            continue
        cell_lower = str(cell).strip().lower()
        # Remove dots and special chars for matching
        cell_cleaned = re.sub(r"[.\-/\\()]", " ", cell_lower).strip()
        if cell_lower in header_keywords or cell_cleaned in header_keywords:
            matches += 1
        # Partial match
        for kw in header_keywords:
            if kw in cell_lower:
                matches += 1
                break

    # Need at least 2 header-like cells (e.g., "Date" and "Amount")
    return matches >= 2


def _deduplicate_columns(columns: list) -> list:
    """Ensure column names are unique by appending suffixes."""
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
