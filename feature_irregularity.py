"""
AML Feature: Irregularity Score Analysis
"""

import pandas as pd
import numpy as np


def feature_irregularity(transactions_df, partner_id=None):
    """
    Compute irregularity score based on transaction patterns.

    Analyzes variance in amounts, timing irregularity, and pattern breaks.

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
        print(f"Feature: Irregularity – {label} – No transactions found")
        return

    # Sort by date
    df = df.sort_values('Date')

    # Amount variance (coefficient of variation)
    amounts = df['Amount'].abs()
    cv_amount = (amounts.std() / amounts.mean()) if amounts.mean() > 0 else 0

    # Timing irregularity: variance in time between transactions
    if len(df) > 1:
        df['time_diff'] = df['Date'].diff().dt.total_seconds() / 3600  # hours
        time_diffs = df['time_diff'].dropna()
        cv_timing = (time_diffs.std() / time_diffs.mean()) if time_diffs.mean() > 0 else 0
    else:
        cv_timing = 0

    # Day of week variance
    df['day_of_week'] = df['Date'].dt.dayofweek
    day_distribution = df['day_of_week'].value_counts()
    day_entropy = -(day_distribution / len(df) * np.log(day_distribution / len(df) + 1e-10)).sum()

    # Composite irregularity score (normalized 0-100)
    irregularity_score = min(100, (cv_amount * 20 + cv_timing * 10 + day_entropy * 10))

    # Risk assessment
    if irregularity_score > 60:
        risk = "HIGH"
    elif irregularity_score > 30:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    print(f"Feature: Irregularity – {label}")
    print(f"  Amount irregularity (CV): {cv_amount:.2f}")
    print(f"  Timing irregularity (CV): {cv_timing:.2f}")
    print(f"  Day distribution entropy: {day_entropy:.2f}")
    print(f"  Composite irregularity score: {irregularity_score:.1f}/100")
    print(f"  Risk: {risk}")
    print()


if __name__ == '__main__':
    from aml_utils import load_data

    # Load data
    transactions_df, accounts_df = load_data()

    # Test global analysis
    print("=== Global Analysis ===")
    feature_irregularity(transactions_df)

    # Test individual partner analysis
    sample_partner = transactions_df['partner_id'].value_counts().index[0]
    print(f"\n=== Individual Analysis: {sample_partner} ===")
    feature_irregularity(transactions_df, partner_id=sample_partner)
