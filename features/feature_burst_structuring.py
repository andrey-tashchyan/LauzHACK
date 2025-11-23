"""
AML Feature: Burst Detection and Structuring Analysis
Adapted for new transaction schema with incoming/outgoing structure.
"""

import pandas as pd
import numpy as np
from datetime import datetime


def _prepare_transactions(transactions_df, partner_id=None):
    """
    Prepare and normalize transaction data for the new schema.
    See feature_frequency.py for detailed documentation.
    """
    df = transactions_df.copy()

    # Drop unnamed columns
    df = df.drop(columns=[col for col in df.columns if 'Unnamed' in str(col)], errors='ignore')

    # Convert Date to datetime
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')

    # Derive logical columns based on Debit/Credit direction
    df['logical_partner_id'] = np.where(
        df['Debit/Credit'] == 'debit',
        df['partner_id_outgoing'],
        df['partner_id_incoming']
    )

    df['counterparty_id'] = np.where(
        df['Debit/Credit'] == 'debit',
        df['partner_id_incoming'],
        df['partner_id_outgoing']
    )

    # Filter by partner_id if specified
    if partner_id:
        df = df[df['logical_partner_id'] == partner_id]

    return df


def feature_burst_structuring(transactions_df, partner_id=None, return_data=True):
    """
    Detect bursts of transactions and potential structuring patterns.

    Identifies:
    - Clusters of many transactions in short time windows
    - Transactions just below reporting thresholds (structuring/smurfing)

    This version is adapted for the new transaction schema with incoming/outgoing structure.

    Parameters:
    -----------
    transactions_df : pd.DataFrame
        Transaction data with new schema (includes Debit/Credit, incoming/outgoing fields)
    partner_id : str, optional
        Specific partner to analyze
    return_data : bool, optional
        If True, returns dictionary with computed metrics. Default: True.

    Returns:
    --------
    dict or None : If return_data=True, returns metrics dictionary
    """
    # Prepare and normalize data
    df = _prepare_transactions(transactions_df, partner_id)

    if partner_id:
        label = f"Partner {partner_id}"
    else:
        label = "All partners"

    if len(df) == 0:
        print(f"Feature: Burst/Structuring – {label} – No transactions found")
        if return_data:
            return {
                "feature_name": "burst_structuring",
                "partner_id": partner_id if partner_id else "global",
                "partner_name": None,
                "metrics": {
                    "burst_hours": 0,
                    "max_burst": 0,
                    "structuring_count": 0,
                    "total_transactions": 0
                },
                "risk_level": "LOW",
                "risk_score": 0,
                "risk_reasons": ["No transactions found"],
                "timestamp": datetime.now().isoformat()
            }
        return None

    # Sort by date
    df = df.sort_values('Date')

    # Detect bursts: more than 5 transactions within 1 hour
    df['hour_window'] = df['Date'].dt.floor('h')
    hourly_counts = df.groupby(['logical_partner_id', 'hour_window']).size()
    burst_hours = (hourly_counts > 5).sum()
    max_burst = hourly_counts.max() if len(hourly_counts) > 0 else 0

    # Detect structuring: amounts just below common thresholds
    # Common thresholds: 10000, 9000, 5000
    thresholds = [10000, 9000, 5000]
    structuring_count = 0
    structuring_details = {}

    for threshold in thresholds:
        # Transactions between 80-99% of threshold
        lower = threshold * 0.8
        upper = threshold * 0.99
        count = len(df[(df['Amount'].abs() >= lower) &
                       (df['Amount'].abs() <= upper)])
        structuring_count += count
        if count > 0:
            structuring_details[f"near_{threshold}"] = count

    # Risk assessment
    risk_reasons = []
    if burst_hours > 10 or structuring_count > 20:
        risk = "HIGH"
        risk_score = 90
        if burst_hours > 10:
            risk_reasons.append(f"Detected {burst_hours} hourly bursts (>5 tx/hour), indicating rapid transaction activity")
        if structuring_count > 20:
            risk_reasons.append(f"Found {structuring_count} transactions near reporting thresholds, potential structuring")
    elif burst_hours > 3 or structuring_count > 5:
        risk = "MEDIUM"
        risk_score = 60
        if burst_hours > 3:
            risk_reasons.append(f"Detected {burst_hours} hourly bursts")
        if structuring_count > 5:
            risk_reasons.append(f"Found {structuring_count} transactions near thresholds")
    else:
        risk = "LOW"
        risk_score = 15
        risk_reasons.append("No significant burst or structuring patterns detected")

    print(f"Feature: Burst/Structuring – {label}")
    print(f"  Total transactions: {len(df)}")
    print(f"  Burst hours (>5 tx/hour): {burst_hours}")
    print(f"  Max transactions in 1 hour: {max_burst}")
    print(f"  Potential structuring patterns: {structuring_count}")
    if structuring_details:
        for threshold, count in structuring_details.items():
            print(f"    - {threshold}: {count} transactions")
    print(f"  Risk: {risk} (score: {risk_score}/100)")
    if risk_reasons:
        print(f"  Reasons: {'; '.join(risk_reasons)}")
    print()

    # Return structured data
    if return_data:
        return {
            "feature_name": "burst_structuring",
            "partner_id": partner_id if partner_id else "global",
            "partner_name": None,
            "metrics": {
                "total_transactions": len(df),
                "burst_hours": int(burst_hours),
                "max_burst": int(max_burst),
                "structuring_count": int(structuring_count),
                "structuring_details": structuring_details
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
    result = feature_burst_structuring(transactions_df, return_data=True)

    # Test individual partner analysis
    if 'partner_id_incoming' in transactions_df.columns:
        sample_partners = pd.concat([
            transactions_df['partner_id_incoming'].dropna(),
            transactions_df['partner_id_outgoing'].dropna()
        ]).value_counts()

        if len(sample_partners) > 0:
            sample_partner = sample_partners.index[0]
            print(f"\n=== Individual Analysis: {sample_partner} ===")
            result = feature_burst_structuring(transactions_df, partner_id=sample_partner, return_data=True)
