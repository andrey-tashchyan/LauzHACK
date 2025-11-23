"""
AML Feature: Transaction Frequency Analysis
Adapted for new transaction schema with incoming/outgoing structure.
"""

import pandas as pd
import numpy as np
from datetime import datetime


def _prepare_transactions(transactions_df, partner_id=None):
    """
    Prepare and normalize transaction data for the new schema.

    This helper function:
    - Drops unnamed columns
    - Converts 'Date' to datetime
    - Derives logical partner_id, counterparty_id, and country fields
    - Handles the dual incoming/outgoing structure

    Strategy:
    - For 'debit' transactions: the outgoing side is the logical partner
    - For 'credit' transactions: the incoming side is the logical partner
    - The opposite side becomes the counterparty

    Parameters:
    -----------
    transactions_df : pd.DataFrame
        Raw transaction data with new schema
    partner_id : str, optional
        Partner ID to filter on

    Returns:
    --------
    pd.DataFrame : Cleaned and normalized transaction data
    """
    df = transactions_df.copy()

    # Drop unnamed columns
    df = df.drop(columns=[col for col in df.columns if 'Unnamed' in str(col)], errors='ignore')

    # Convert Date to datetime
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')

    # Derive logical columns based on Debit/Credit direction
    # For debit: we send money, so outgoing = us (partner), incoming = counterparty
    # For credit: we receive money, so incoming = us (partner), outgoing = counterparty

    df['logical_partner_id'] = np.where(
        df['Debit/Credit'] == 'debit',
        df['partner_id_outgoing'],
        df['partner_id_incoming']
    )

    df['logical_partner_country'] = np.where(
        df['Debit/Credit'] == 'debit',
        df['country_name_outgoing'],
        df['country_name_incoming']
    )

    df['logical_partner_sector'] = np.where(
        df['Debit/Credit'] == 'debit',
        df['industry_gic2_code_outgoing'],
        df['industry_gic2_code_incoming']
    )

    df['counterparty_id'] = np.where(
        df['Debit/Credit'] == 'debit',
        df['partner_id_incoming'],
        df['partner_id_outgoing']
    )

    df['counterparty_country'] = np.where(
        df['Debit/Credit'] == 'debit',
        df['country_name_incoming'],
        df['country_name_outgoing']
    )

    df['counterparty_sector'] = np.where(
        df['Debit/Credit'] == 'debit',
        df['industry_gic2_code_incoming'],
        df['industry_gic2_code_outgoing']
    )

    df['counterparty_account_id'] = np.where(
        df['Debit/Credit'] == 'debit',
        df['account_id_incoming'],
        df['account_id_outgoing']
    )

    # Also handle external counterparty fields
    if 'ext_counterparty_country' in df.columns:
        df['counterparty_country'] = df['counterparty_country'].fillna(df['ext_counterparty_country'])

    # Filter by partner_id if specified
    if partner_id:
        df = df[df['logical_partner_id'] == partner_id]

    return df


def feature_frequency(transactions_df, partner_id=None, return_data=True):
    """
    Analyze transaction frequency over time.

    Computes the number of transactions per day/week and identifies
    patterns that may indicate suspicious activity.

    This version is adapted for the new transaction schema with incoming/outgoing structure.

    Parameters:
    -----------
    transactions_df : pd.DataFrame
        Transaction data with new schema (includes Debit/Credit, incoming/outgoing fields)
    partner_id : str, optional
        Specific partner to analyze. If None, analyzes all transactions.
    return_data : bool, optional
        If True, returns dictionary with computed metrics. Default: True.

    Returns:
    --------
    dict or None : If return_data=True, returns metrics dictionary
    """
    # Prepare and normalize data
    df = _prepare_transactions(transactions_df, partner_id)

    # Set label for output
    if partner_id:
        label = f"Partner {partner_id}"
    else:
        label = "All partners"

    if len(df) == 0:
        print(f"Feature: Frequency – {label} – No transactions found")
        if return_data:
            return {
                "feature_name": "frequency",
                "partner_id": partner_id if partner_id else "global",
                "partner_name": None,
                "metrics": {
                    "total_transactions": 0,
                    "date_range_days": 0,
                    "tx_per_day_avg": 0,
                    "max_daily": 0,
                    "avg_daily": 0,
                    "std_daily": 0
                },
                "risk_level": "LOW",
                "risk_score": 0,
                "risk_reasons": ["No transactions found"],
                "timestamp": datetime.now().isoformat()
            }
        return None

    # Calculate metrics
    total_tx = len(df)
    min_date = df['Date'].min()
    max_date = df['Date'].max()
    date_range = (max_date - min_date).days
    if date_range == 0:
        date_range = 1

    tx_per_day = total_tx / date_range

    # Daily transaction counts
    daily_counts = df.groupby(df['Date'].dt.date).size()
    max_daily = daily_counts.max() if len(daily_counts) > 0 else 0
    avg_daily = daily_counts.mean() if len(daily_counts) > 0 else 0
    std_daily = daily_counts.std() if len(daily_counts) > 0 else 0

    # Percentiles
    percentiles = {
        "25": float(daily_counts.quantile(0.25)) if len(daily_counts) > 0 else 0,
        "50": float(daily_counts.quantile(0.50)) if len(daily_counts) > 0 else 0,
        "75": float(daily_counts.quantile(0.75)) if len(daily_counts) > 0 else 0,
        "90": float(daily_counts.quantile(0.90)) if len(daily_counts) > 0 else 0
    }

    # Risk assessment
    risk_reasons = []
    if tx_per_day > 10:
        risk = "HIGH"
        risk_score = 85
        risk_reasons.append(f"Transaction frequency ({tx_per_day:.2f} tx/day) significantly exceeds normal threshold (10 tx/day)")
    elif tx_per_day > 3:
        risk = "MEDIUM"
        risk_score = 55
        risk_reasons.append(f"Transaction frequency ({tx_per_day:.2f} tx/day) moderately elevated above threshold (3 tx/day)")
    else:
        risk = "LOW"
        risk_score = 20
        risk_reasons.append(f"Transaction frequency ({tx_per_day:.2f} tx/day) within normal range")

    if max_daily > tx_per_day * 2:
        risk_reasons.append(f"Peak daily volume ({max_daily} tx) is {max_daily/tx_per_day:.1f}x the average, indicating bursts")

    print(f"Feature: Frequency – {label}")
    print(f"  Total transactions: {total_tx}")
    print(f"  Period: {date_range} days")
    print(f"  Average: {tx_per_day:.2f} tx/day")
    print(f"  Max daily: {max_daily} tx")
    print(f"  Risk: {risk} (score: {risk_score}/100)")
    if risk_reasons:
        print(f"  Reasons: {'; '.join(risk_reasons)}")
    print()

    # Return structured data
    if return_data:
        return {
            "feature_name": "frequency",
            "partner_id": partner_id if partner_id else "global",
            "partner_name": None,  # Will be filled by run_all_features
            "metrics": {
                "total_transactions": int(total_tx),
                "date_range_days": int(date_range),
                "start_date": min_date.isoformat(),
                "end_date": max_date.isoformat(),
                "tx_per_day_avg": round(float(tx_per_day), 2),
                "max_daily": int(max_daily),
                "avg_daily": round(float(avg_daily), 2),
                "std_daily": round(float(std_daily), 2),
                "percentiles": percentiles,
                "daily_distribution": daily_counts.tolist() if len(daily_counts) <= 365 else daily_counts.tail(365).tolist()
            },
            "risk_level": risk,
            "risk_score": risk_score,
            "risk_reasons": risk_reasons,
            "timestamp": datetime.now().isoformat()
        }


if __name__ == '__main__':
    # Test with sample data
    sample_file = '/Users/tashchyan/Desktop/LauzHACK/features/sample_data_100 (1).csv'

    print("Loading sample data...")
    transactions_df = pd.read_csv(sample_file)

    # Test global analysis
    print("=== Global Analysis ===")
    result = feature_frequency(transactions_df, return_data=True)

    # Test individual partner analysis
    if 'partner_id_incoming' in transactions_df.columns:
        sample_partners = pd.concat([
            transactions_df['partner_id_incoming'].dropna(),
            transactions_df['partner_id_outgoing'].dropna()
        ]).value_counts()

        if len(sample_partners) > 0:
            sample_partner = sample_partners.index[0]
            print(f"\n=== Individual Analysis: {sample_partner} ===")
            result = feature_frequency(transactions_df, partner_id=sample_partner, return_data=True)
