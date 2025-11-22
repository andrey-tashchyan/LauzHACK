"""
AML Feature: Burst Detection and Structuring Analysis
"""

import pandas as pd


def feature_burst_structuring(transactions_df, partner_id=None):
    """
    Detect bursts of transactions and potential structuring patterns.

    Identifies:
    - Clusters of many transactions in short time windows
    - Transactions just below reporting thresholds (structuring/smurfing)

    Parameters:
    -----------
    transactions_df : pd.DataFrame
        Transaction data
    partner_id : str, optional
        Specific partner to analyze
    """
    df = transactions_df.copy()

    if partner_id:
        df = df[df['partner_id'] == partner_id]
        label = f"Partner {partner_id}"
    else:
        label = "All partners"

    if len(df) == 0:
        print(f"Feature: Burst/Structuring – {label} – No transactions found")
        return

    # Sort by date
    df = df.sort_values('Date')

    # Detect bursts: more than 5 transactions within 1 hour
    df['hour_window'] = df['Date'].dt.floor('h')
    hourly_counts = df.groupby(['partner_id', 'hour_window']).size()
    burst_hours = (hourly_counts > 5).sum()
    max_burst = hourly_counts.max() if len(hourly_counts) > 0 else 0

    # Detect structuring: amounts just below common thresholds
    # Common thresholds: 10000, 9000, 5000
    thresholds = [10000, 9000, 5000]
    structuring_count = 0

    for threshold in thresholds:
        # Transactions between 80-99% of threshold
        lower = threshold * 0.8
        upper = threshold * 0.99
        structuring_count += len(df[(df['Amount'].abs() >= lower) &
                                    (df['Amount'].abs() <= upper)])

    # Risk assessment
    if burst_hours > 10 or structuring_count > 20:
        risk = "HIGH"
    elif burst_hours > 3 or structuring_count > 5:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    print(f"Feature: Burst/Structuring – {label}")
    print(f"  Burst hours (>5 tx/hour): {burst_hours}")
    print(f"  Max transactions in 1 hour: {max_burst}")
    print(f"  Potential structuring patterns: {structuring_count}")
    print(f"  Risk: {risk}")
    print()


if __name__ == '__main__':
    from aml_utils import load_data

    # Load data
    transactions_df, accounts_df = load_data()

    # Test global analysis
    print("=== Global Analysis ===")
    feature_burst_structuring(transactions_df)

    # Test individual partner analysis
    sample_partner = transactions_df['partner_id'].value_counts().index[0]
    print(f"\n=== Individual Analysis: {sample_partner} ===")
    feature_burst_structuring(transactions_df, partner_id=sample_partner)
