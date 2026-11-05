"""
Transaction analytics: frequency, totals, summaries.
"""

import pandas as pd


def analyze_transactions(df: pd.DataFrame) -> dict:
    """
    Analyze a normalized transaction DataFrame.

    Args:
        df: DataFrame with columns [Date, Name, Dr, Cr, Remark]

    Returns:
        Dictionary with:
            - name_frequency: list of {name, frequency, total_dr, total_cr}
              sorted by frequency descending
            - summary: {total_dr, total_cr, net_balance, transaction_count, date_range}
    """
    # Ensure numeric columns
    df = df.copy()
    df["Dr"] = pd.to_numeric(df["Dr"], errors="coerce").fillna(0.0)
    df["Cr"] = pd.to_numeric(df["Cr"], errors="coerce").fillna(0.0)

    # --- Name frequency & totals ---
    name_groups = (
        df.groupby("Name", dropna=False)
        .agg(
            frequency=("Name", "count"),
            total_dr=("Dr", "sum"),
            total_cr=("Cr", "sum"),
        )
        .reset_index()
    )
    name_groups = name_groups.sort_values("frequency", ascending=False)

    name_frequency = []
    for _, row in name_groups.iterrows():
        name_frequency.append({
            "name": str(row["Name"]) if pd.notna(row["Name"]) else "UNKNOWN",
            "frequency": int(row["frequency"]),
            "total_dr": round(float(row["total_dr"]), 2),
            "total_cr": round(float(row["total_cr"]), 2),
        })

    # --- Summary ---
    total_dr = round(float(df["Dr"].sum()), 2)
    total_cr = round(float(df["Cr"].sum()), 2)
    net_balance = round(total_cr - total_dr, 2)
    transaction_count = len(df)

    # Date range
    date_range = _get_date_range(df)
    start_val = date_range.get("start")
    end_val = date_range.get("end")

    summary = {
        "total_dr": total_dr,
        "total_cr": total_cr,
        "net_balance": net_balance,
        "transaction_count": transaction_count,
        "date_range": {
            "from": start_val,
            "to": end_val,
            "start": start_val,
            "end": end_val,
        },
    }

    return {
        "name_frequency": name_frequency,
        "summary": summary,
    }


def _get_date_range(df: pd.DataFrame) -> dict:
    """Extract the date range from the Date column."""
    dates = df["Date"].dropna()
    if dates.empty:
        return {"start": None, "end": None}

    # Try to parse dates
    parsed = pd.to_datetime(dates, errors="coerce", dayfirst=True)
    valid_dates = parsed.dropna()

    if valid_dates.empty:
        # Return raw first/last
        return {
            "start": str(dates.iloc[0]),
            "end": str(dates.iloc[-1]),
        }

    return {
        "start": valid_dates.min().strftime("%d-%m-%Y"),
        "end": valid_dates.max().strftime("%d-%m-%Y"),
    }
