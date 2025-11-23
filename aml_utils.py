"""
Utility loader for AML feature scripts.

Provides a lightweight `load_data` function so that feature modules importing it
can operate without depending on external paths.
"""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data_lauzhack_2"


def _parse_dates(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def load_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load transactions and accounts data with reasonable defaults.
    """
    tx_candidates = [
        ROOT / "joined_with_transactions.csv",
        ROOT / "joined_with_transcation.csv",
        DATA_DIR / "joined_with_transactions.csv",
        DATA_DIR / "joined_with_transcation.csv",
        DATA_DIR / "transactions.csv",
    ]

    tx_path = next((p for p in tx_candidates if p.exists()), None)
    if tx_path is None:
        raise FileNotFoundError("No transaction CSV found for load_data.")

    tx_df = pd.read_csv(tx_path)
    if "Date" in tx_df.columns:
        tx_df["Date"] = pd.to_datetime(tx_df["Date"], errors="coerce")
        tx_df = tx_df.dropna(subset=["Date"]).copy()
    if "Amount" in tx_df.columns:
        tx_df["Amount"] = pd.to_numeric(tx_df["Amount"], errors="coerce").fillna(0.0)
    if "account_id" not in tx_df.columns and "Account ID" in tx_df.columns:
        tx_df["account_id"] = tx_df["Account ID"]

    account_df = pd.read_csv(DATA_DIR / "account.csv")
    account_df = _parse_dates(account_df, ["account_open_date", "account_close_date"])
    return tx_df, account_df
