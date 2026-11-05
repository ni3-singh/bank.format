"""
Bank format detection and description cleaning.

Supports: IDBI, Kotak, SBI, HDFC, and a generic fallback.
"""

import re
from typing import Optional, Tuple

# Keywords to skip when extracting counterparty names
SKIP_KEYWORDS = {
    "UPI", "NEFT", "IMPS", "RTGS", "DR", "CR", "PAY", "PAYMENT", "PAID",
    "TRF", "TRANSFER", "INB", "MOB", "NET", "CASH", "ATM", "CHQ", "CHEQUE",
    "BIL", "BILL", "EMI", "ECS", "ACH", "NACH", "FT", "IFT", "REF", "BY",
    "TO", "FROM", "VIA", "CREDIT", "DEBIT", "REVERSAL", "REV", "CHARGE",
    "CHARGES", "INT", "INTEREST", "TAX", "GST", "TDS", "CGST", "SGST",
    "IGST", "CMS", "SELF", "ONLINE", "MOBILE", "BANKING", "TRANSACTION",
    "MB", "NB", "IB", "NBK", "MBK", "IBK", "WHATSAPP", "GOOGLE", "PHONEPE",
    "PAYTM", "AMAZONPAY", "PAY BY", "PAY", "COLLECTED",
}


def _normalize_header(col: str) -> str:
    """Lowercase, strip, collapse whitespace for header matching."""
    if col is None:
        return ""
    return re.sub(r"\s+", " ", str(col).strip().lower())


def _headers_set(df) -> set:
    """Return a set of normalized column headers."""
    return {_normalize_header(c) for c in df.columns}


def detect_bank_format(df) -> str:
    """
    Detect bank format from DataFrame column headers and data patterns.

    Returns one of: 'idbi', 'kotak', 'sbi', 'hdfc', 'generic'
    """
    headers = _headers_set(df)
    raw_headers = [str(c).strip().lower() for c in df.columns]
    header_str = " ".join(raw_headers)

    # --- IDBI Bank ---
    # Typically has: Transaction Date, Value Date, Description, Ref No./Cheque No.,
    #   Debit, Credit, Balance
    idbi_markers = {"debit", "credit", "description"}
    if idbi_markers.issubset(headers):
        # Check description patterns for UPI/xxx/xxx style (slash separated, 3+ parts)
        descs = _sample_descriptions(df)
        slash_count = sum(1 for d in descs if d.count("/") >= 2)
        if slash_count >= len(descs) * 0.3:
            # Could be IDBI or HDFC – distinguish by segment structure
            # HDFC typically has UPI/DR/number/NAME, IDBI has UPI/number/NAME
            hdfc_pattern = sum(
                1 for d in descs
                if re.match(r"(?i)^(UPI|NEFT|IMPS)/(DR|CR)/", d)
            )
            if hdfc_pattern >= len(descs) * 0.2:
                return "hdfc"
            return "idbi"
        return "idbi"

    # --- Kotak Bank ---
    # Typically has a "Dr / Cr" or "dr/cr" indicator column alongside a single amount
    kotak_indicators = [h for h in raw_headers if "dr" in h and "cr" in h]
    if kotak_indicators:
        return "kotak"
    # Alternate: look for "dr / cr" or "dr/cr" column
    for h in raw_headers:
        if re.search(r"dr\s*/\s*cr", h):
            return "kotak"

    # --- SBI Bank ---
    # SBI uses hyphen-separated descriptions: UPI-NAME-UPI_ID-REMARKS
    # Headers often: Txn Date, Value Date, Description, Ref No./Cheque No., Debit, Credit, Balance
    sbi_header_hints = {"txn date", "value date"}
    if sbi_header_hints.issubset(headers) or any("txn" in h for h in raw_headers):
        descs = _sample_descriptions(df)
        hyphen_count = sum(1 for d in descs if d.count("-") >= 2)
        if hyphen_count >= len(descs) * 0.3:
            return "sbi"

    # --- HDFC Bank ---
    # HDFC has: Date, Narration, Chq./Ref.No., Value Dt, Withdrawal Amt., Deposit Amt., Closing Balance
    hdfc_markers_1 = {"narration", "withdrawal amt.", "deposit amt."}
    hdfc_markers_2 = {"narration", "withdrawal", "deposit"}
    if hdfc_markers_1.issubset(headers) or hdfc_markers_2.issubset(headers):
        return "hdfc"
    if any("narration" in h for h in raw_headers):
        return "hdfc"

    # Check description patterns as a last resort
    descs = _sample_descriptions(df)
    if descs:
        # HDFC pattern: UPI/DR/number/NAME
        hdfc_pattern = sum(
            1 for d in descs
            if re.match(r"(?i)^(UPI|NEFT|IMPS)/(DR|CR)/", d)
        )
        if hdfc_pattern >= len(descs) * 0.3:
            return "hdfc"

        # SBI pattern: UPI-NAME-upiid-remarks
        hyphen_count = sum(1 for d in descs if d.count("-") >= 2)
        slash_count = sum(1 for d in descs if d.count("/") >= 2)
        if hyphen_count > slash_count and hyphen_count >= len(descs) * 0.3:
            return "sbi"

    return "generic"


def _sample_descriptions(df, max_samples: int = 30) -> list:
    """Get a sample of non-empty description strings from likely description columns."""
    desc_col = _find_description_column(df)
    if desc_col is None:
        return []

    descs = []
    for val in df[desc_col].dropna().head(max_samples):
        s = str(val).strip()
        if s and s.lower() not in ("description", "narration", "particulars", "details"):
            descs.append(s)
    return descs


def _find_description_column(df) -> Optional[str]:
    """Find the description/narration column in a DataFrame."""
    desc_keywords = ["description", "narration", "particulars", "details", "remark", "transaction details"]
    for col in df.columns:
        norm = _normalize_header(col)
        for kw in desc_keywords:
            if kw in norm:
                return col
    # Fallback: pick the column with the longest average string length
    str_cols = df.select_dtypes(include=["object"]).columns
    if len(str_cols) > 0:
        avg_lengths = {
            c: df[c].dropna().astype(str).str.len().mean()
            for c in str_cols
        }
        return max(avg_lengths, key=avg_lengths.get)
    return None


def clean_description(description: str, bank_format: str) -> str:
    """
    Extract the counterparty name from a bank transaction description.

    Args:
        description: Raw description string from the bank statement.
        bank_format: One of 'idbi', 'kotak', 'sbi', 'hdfc', 'generic'.

    Returns:
        Cleaned counterparty name.
    """
    if not description or not isinstance(description, str):
        return "UNKNOWN"

    # Normalize: strip, collapse whitespace, remove embedded newlines
    desc = re.sub(r"[\r\n\x0a\x0d]+", " ", description)
    desc = re.sub(r"\s+", " ", desc).strip()

    if not desc:
        return "UNKNOWN"

    extractors = {
        "idbi": _extract_name_idbi,
        "kotak": _extract_name_kotak,
        "sbi": _extract_name_sbi,
        "hdfc": _extract_name_hdfc,
        "generic": _extract_name_generic,
    }

    extractor = extractors.get(bank_format, _extract_name_generic)
    name = extractor(desc)

    # Final cleanup
    name = re.sub(r"\s+", " ", name).strip()
    name = name.strip("/- ")

    if not name or len(name) < 2:
        return _fallback_clean(desc)

    return name.title()


def _extract_name_idbi(desc: str) -> str:
    """
    IDBI: UPI/131957696956/Shree ganesh trade centre → 3rd segment
    Pattern: TYPE/TRANSACTION_ID/NAME[/extra...]
    """
    parts = [p.strip() for p in desc.split("/") if p.strip()]

    if len(parts) >= 3:
        # Check if first part is a transaction type keyword
        if parts[0].upper() in ("UPI", "NEFT", "IMPS", "RTGS", "FT", "IFT"):
            # 3rd segment is the name
            candidate = parts[2]
            if _is_valid_name(candidate):
                return candidate
            # Try other segments
            for p in parts[2:]:
                if _is_valid_name(p):
                    return p

    return _extract_name_generic(desc)


def _extract_name_kotak(desc: str) -> str:
    """
    Kotak: UPI/JYOTI KIRANA AN/122420711368/PAY BY WHATSAPP → 2nd segment
    Pattern: TYPE/NAME/TRANSACTION_ID/REMARKS
    """
    parts = [p.strip() for p in desc.split("/") if p.strip()]

    if len(parts) >= 2:
        if parts[0].upper() in ("UPI", "NEFT", "IMPS", "RTGS", "FT", "IFT"):
            candidate = parts[1]
            if _is_valid_name(candidate):
                return candidate
            # Try other non-numeric segments
            for p in parts[1:]:
                if _is_valid_name(p):
                    return p

    return _extract_name_generic(desc)


def _extract_name_sbi(desc: str) -> str:
    """
    SBI: UPI-NAME-UPI_ID-REMARKS → 2nd segment (hyphen separated)
    Also handles: NEFT-NAME-REMARKS, IMPS-NAME-REMARKS
    """
    parts = [p.strip() for p in desc.split("-") if p.strip()]

    if len(parts) >= 2:
        first_upper = parts[0].upper().strip()
        if first_upper in ("UPI", "NEFT", "IMPS", "RTGS", "FT", "IFT", "ACH", "ECS", "NACH"):
            candidate = parts[1]
            if _is_valid_name(candidate):
                return candidate
            for p in parts[1:]:
                if _is_valid_name(p):
                    return p

    # Try slash splitting as fallback
    return _extract_name_generic(desc)


def _extract_name_hdfc(desc: str) -> str:
    """
    HDFC: UPI/DR/412345678901/JOHN DOE/hdfc/remarks → 4th segment (NAME)
    Pattern: TYPE/DR_CR/TRANSACTION_ID/NAME/BANK/REMARKS
    """
    parts = [p.strip() for p in desc.split("/") if p.strip()]

    if len(parts) >= 4:
        first_upper = parts[0].upper()
        if first_upper in ("UPI", "NEFT", "IMPS", "RTGS", "FT", "IFT"):
            # Check if 2nd part is DR/CR indicator
            if parts[1].upper() in ("DR", "CR"):
                # 4th segment (index 3) is the name
                candidate = parts[3]
                if _is_valid_name(candidate):
                    return candidate
            else:
                # No DR/CR indicator – try index 2 or 3
                for idx in [2, 3, 1]:
                    if idx < len(parts) and _is_valid_name(parts[idx]):
                        return parts[idx]

    # Fallback to generic for NEFT/IMPS with different patterns
    return _extract_name_generic(desc)


def _extract_name_generic(desc: str) -> str:
    """
    Generic handler: try splitting by / and -, apply heuristics.
    """
    # Try slash-separated first
    slash_parts = [p.strip() for p in desc.split("/") if p.strip()]
    if len(slash_parts) >= 2:
        name = _pick_best_name(slash_parts)
        if name:
            return name

    # Try hyphen-separated
    hyphen_parts = [p.strip() for p in desc.split("-") if p.strip()]
    if len(hyphen_parts) >= 2:
        name = _pick_best_name(hyphen_parts)
        if name:
            return name

    return _fallback_clean(desc)


def _pick_best_name(parts: list) -> Optional[str]:
    """Pick the best candidate name from a list of description segments."""
    candidates = []
    for i, part in enumerate(parts):
        p = part.strip()
        if not p:
            continue
        if p.upper() in SKIP_KEYWORDS:
            continue
        if re.match(r"^\d+$", p):
            continue
        if re.match(r"^[\d\s@.\-]+$", p):
            continue
        # Skip very short segments (likely codes)
        if len(p) < 3:
            continue
        # Skip segments that look like UPI IDs (contain @)
        if "@" in p:
            continue
        # Prefer segments with alphabetic characters
        alpha_ratio = sum(1 for c in p if c.isalpha()) / max(len(p), 1)
        if alpha_ratio >= 0.5:
            candidates.append((i, p, alpha_ratio))

    if not candidates:
        return None

    # Prefer candidates with higher alpha ratio, and among ties, earlier position
    # but skip index 0 if it looks like a transaction type
    filtered = [c for c in candidates if c[0] > 0]
    if not filtered:
        filtered = candidates

    # Sort by alpha ratio descending, then by position ascending
    filtered.sort(key=lambda x: (-x[2], x[0]))
    return filtered[0][1]


def _is_valid_name(s: str) -> bool:
    """Check if a string looks like a valid counterparty name."""
    if not s or len(s) < 2:
        return False
    s = s.strip()
    if s.upper() in SKIP_KEYWORDS:
        return False
    # Reject pure numbers
    if re.match(r"^[\d\s,.\-]+$", s):
        return False
    # Reject UPI IDs
    if "@" in s:
        return False
    # Must have some alphabetic content
    alpha_ratio = sum(1 for c in s if c.isalpha()) / max(len(s), 1)
    return alpha_ratio >= 0.4


def _fallback_clean(desc: str) -> str:
    """Last resort: clean the full description for use as a name."""
    # Remove common prefixes
    cleaned = re.sub(
        r"(?i)^(UPI|NEFT|IMPS|RTGS|FT|IFT|ACH|ECS|NACH|ATM|CHQ|CHEQUE)[\s/\-:]*",
        "",
        desc,
    )
    # Remove transaction IDs (long numbers)
    cleaned = re.sub(r"\b\d{6,}\b", "", cleaned)
    # Remove UPI IDs
    cleaned = re.sub(r"\S+@\S+", "", cleaned)
    # Remove DR/CR markers
    cleaned = re.sub(r"\b(DR|CR)\b", "", cleaned, flags=re.IGNORECASE)
    # Collapse separators
    cleaned = re.sub(r"[/\-]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if len(cleaned) < 2:
        return desc.strip()[:50] if desc else "UNKNOWN"

    # Truncate if too long
    if len(cleaned) > 60:
        cleaned = cleaned[:60].rsplit(" ", 1)[0]

    return cleaned


def normalize_dr_cr(row: dict, bank_format: str, amount_col: str = None,
                    dr_col: str = None, cr_col: str = None,
                    indicator_col: str = None) -> Tuple[float, float]:
    """
    Normalize debit and credit amounts from a row.

    Handles:
    - Separate DR/CR columns (IDBI, SBI, HDFC)
    - Single amount column with DR/CR indicator (Kotak)

    Returns:
        Tuple of (debit_amount, credit_amount) as floats.
    """
    if bank_format == "kotak" and amount_col and indicator_col:
        # Single amount column with indicator
        amount = _parse_amount(row.get(amount_col))
        indicator = str(row.get(indicator_col, "")).strip().upper()
        if indicator == "DR" or indicator == "D":
            return (amount, 0.0)
        elif indicator == "CR" or indicator == "C":
            return (0.0, amount)
        else:
            # If no indicator, try to guess from sign
            if amount < 0:
                return (abs(amount), 0.0)
            return (0.0, amount)

    # Separate columns
    dr = _parse_amount(row.get(dr_col)) if dr_col else 0.0
    cr = _parse_amount(row.get(cr_col)) if cr_col else 0.0
    return (dr, cr)


def _parse_amount(value) -> float:
    """
    Parse an amount value that may contain commas, spaces, currency symbols, or be empty/None.

    Returns:
        Float amount, 0.0 if unparseable.
    """
    if value is None:
        return 0.0

    s = str(value).strip()

    if not s or s.lower() in ("", "nan", "none", "null", "-", "--", "nil"):
        return 0.0

    # Remove currency symbols, commas, spaces
    s = re.sub(r"[₹$€£,\s]", "", s)

    # Handle parenthetical negatives: (1234.56) → -1234.56
    match = re.match(r"^\(([0-9.]+)\)$", s)
    if match:
        return -float(match.group(1))

    # Handle trailing DR/CR indicators
    cr_match = re.match(r"^([0-9.]+)\s*(CR|Cr|cr)$", s)
    if cr_match:
        return float(cr_match.group(1))

    dr_match = re.match(r"^([0-9.]+)\s*(DR|Dr|dr)$", s)
    if dr_match:
        return float(dr_match.group(1))

    try:
        return abs(float(s))
    except (ValueError, TypeError):
        return 0.0
