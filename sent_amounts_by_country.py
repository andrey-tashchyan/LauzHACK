"""
Aggregate outgoing amounts per counterparty country for a given account.

Examples
--------
python sent_amounts_by_country.py --account-id 2f07ef4f-2dd8-4cd1-94d5-004be5de1ec8
python sent_amounts_by_country.py --account-id 123 --window-days 90 --transactions-file data_lauzhack_2/transactions.csv
python sent_amounts_by_country.py --account-id 123 --start-date 2024-01-01 --end-date 2024-02-01
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

# Default lookback if the user does not provide any window.
DEFAULT_WINDOW_DAYS = 30

# Candidate CSV locations. The first existing file is used unless overridden via CLI.
TRANSACTION_CSV_CANDIDATES = [
    Path("transactions.csv"),
    Path("data_lauzhack_2/transactions.csv"),
    Path("joined_with_transactions.csv"),
    Path("data_lauzhack_2/joined_with_transactions.csv"),
]


def find_input_file(candidates: List[Path]) -> Path:
    """Return the first existing path among the candidates."""
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError(
        "No transaction CSV found. Update TRANSACTION_CSV_CANDIDATES or pass --transactions-file."
    )


def resolve_columns(df: pd.DataFrame) -> Dict[str, str]:
    """
    Map logical field names to the actual columns present in the dataset.
    Raises if a required column cannot be found.
    """
    candidate_map = {
        "account_id": ["Account ID", "account_id", "account"],
        "date": ["Date", "date", "transaction_date"],
        "amount": ["Amount", "amount", "transaction_amount"],
        "direction": ["Debit/Credit", "debit_credit", "direction"],
        "country": ["ext_counterparty_country", "counterparty_country", "country"],
    }

    resolved: Dict[str, str] = {}
    for logical, candidates in candidate_map.items():
        for col in candidates:
            if col in df.columns:
                resolved[logical] = col
                break

    missing_required = [key for key in ["account_id", "date", "amount", "direction"] if key not in resolved]
    if missing_required:
        raise KeyError(
            f"Missing required columns: {missing_required}. "
            f"Available columns: {list(df.columns)}"
        )

    if "country" not in resolved:
        placeholder = "__country_placeholder__"
        df[placeholder] = "Unknown"
        resolved["country"] = placeholder

    return resolved


def load_transactions(file_path: Path) -> pd.DataFrame:
    """Load the CSV and standardise key columns."""
    df = pd.read_csv(file_path)
    column_map = resolve_columns(df)

    df["tx_date"] = pd.to_datetime(df[column_map["date"]], errors="coerce")
    df = df.dropna(subset=["tx_date"]).copy()

    df["amount_value"] = pd.to_numeric(df[column_map["amount"]], errors="coerce").fillna(0.0)
    df["is_debit"] = (
        df[column_map["direction"]].astype(str).str.lower().str.strip() == "debit"
    )
    df["account_id_value"] = df[column_map["account_id"]].astype(str)
    df["country_clean"] = (
        df[column_map["country"]]
        .fillna("Unknown")
        .astype(str)
        .str.strip()
        .replace({"": "Unknown"})
    )

    return df


def compute_date_bounds(
    df: pd.DataFrame,
    start_date: Optional[str],
    end_date: Optional[str],
    window_days: Optional[int],
) -> Tuple[Optional[pd.Timestamp], Optional[pd.Timestamp]]:
    """Compute start/end bounds based on user input and data availability."""
    end = pd.to_datetime(end_date) if end_date else df["tx_date"].max()
    if pd.isna(end):
        end = pd.Timestamp.utcnow().normalize()

    if window_days is not None:
        start = end - pd.Timedelta(days=window_days)
    elif start_date:
        start = pd.to_datetime(start_date)
    else:
        start = None

    return start, end


def amount_sent_per_country(
    df: pd.DataFrame,
    account_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    window_days: Optional[int] = None,
) -> Tuple[pd.DataFrame, Optional[pd.Timestamp], Optional[pd.Timestamp]]:
    """
    Return a DataFrame with total outgoing amounts per country for the account.
    """
    start, end = compute_date_bounds(df, start_date, end_date, window_days)
    mask = df["account_id_value"] == str(account_id)
    mask &= df["is_debit"]
    if start is not None:
        mask &= df["tx_date"] >= start
    if end is not None:
        mask &= df["tx_date"] <= end

    subset = df.loc[mask].copy()
    grouped = (
        subset.groupby("country_clean")["amount_value"]
        .sum()
        .reset_index(name="total_sent")
        .sort_values("total_sent", ascending=False)
        .reset_index(drop=True)
    )
    return grouped, start, end


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Aggregate outgoing amounts per country for an account over a date window."
    )
    parser.add_argument("--account-id", required=True, help="Account identifier to filter on.")
    parser.add_argument("--transactions-file", type=str, help="Optional path to the transactions CSV.")
    parser.add_argument(
        "--start-date",
        type=str,
        help="Inclusive start date (YYYY-MM-DD). Cannot be combined with --window-days.",
    )
    parser.add_argument("--end-date", type=str, help="Inclusive end date (YYYY-MM-DD).")
    parser.add_argument(
        "--window-days",
        type=int,
        help=f"Lookback window in days counting back from end-date (default {DEFAULT_WINDOW_DAYS}).",
    )
    parser.add_argument(
        "--output-json",
        type=str,
        help="Optional path to write the results (with window and account metadata) as JSON.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.window_days is not None and args.window_days <= 0:
        raise ValueError("--window-days must be a positive integer.")

    if args.start_date and args.window_days is not None:
        raise ValueError("Use either --start-date or --window-days, not both.")

    window_days = args.window_days
    if window_days is None and not args.start_date and not args.end_date:
        window_days = DEFAULT_WINDOW_DAYS

    if args.transactions_file:
        tx_path = Path(args.transactions_file)
        if not tx_path.exists():
            raise FileNotFoundError(f"Transactions file not found: {tx_path}")
    else:
        tx_path = find_input_file(TRANSACTION_CSV_CANDIDATES)

    df = load_transactions(tx_path)
    result, start, end = amount_sent_per_country(
        df,
        account_id=args.account_id,
        start_date=args.start_date,
        end_date=args.end_date,
        window_days=window_days,
    )

    window_label = f"{start.date() if start is not None else '-inf'} -> {end.date() if end is not None else '+inf'}"
    print(f"File: {tx_path}")
    print(f"Account: {args.account_id}")
    print(f"Window: {window_label}")

    if result.empty:
        print("No debit transactions found for the specified filters.")
    else:
        print("\nTotal sent per country:")
        print(result.to_string(index=False))

    if args.output_json:
        payload = {
            "account_id": args.account_id,
            "transactions_file": str(tx_path),
            "window": {
                "start": start.date().isoformat() if start is not None else None,
                "end": end.date().isoformat() if end is not None else None,
            },
            "results": result.to_dict(orient="records"),
        }
        output_path = Path(args.output_json)
        output_path.write_text(json.dumps(payload, indent=2))
        print(f"\nJSON written to {output_path}")


if __name__ == "__main__":
    main()
