"""
AML Feature: Night-Time Activity Analysis
"""

import pandas as pd


def feature_night_activity(transactions_df, partner_id=None):
    """
    Analyze transactions occurring during night hours.

    Computes the proportion of transactions executed between
    22:00 and 06:00, which may indicate suspicious activity.

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
        print(f"Feature: Night Activity – {label} – No transactions found")
        return

    # Extract hour
    df['hour'] = df['Date'].dt.hour

    # Night hours: 22:00 to 06:00
    night_mask = (df['hour'] >= 22) | (df['hour'] < 6)
    night_count = night_mask.sum()
    total_tx = len(df)
    night_pct = (night_count / total_tx) * 100

    # Hour distribution
    hour_dist = df['hour'].value_counts().sort_index()

    # Risk assessment
    if night_pct > 30:
        risk = "HIGH"
    elif night_pct > 10:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    print(f"Feature: Night Activity – {label}")
    print(f"  Total transactions: {total_tx}")
    print(f"  Night transactions (22:00-06:00): {night_count} ({night_pct:.1f}%)")
    print(f"  Peak hour: {hour_dist.idxmax()}:00 ({hour_dist.max()} tx)")
    print(f"  Risk: {risk}")
    print()


if __name__ == '__main__':
    from aml_utils import load_data

    # Load data
    transactions_df, accounts_df = load_data()

    # Test global analysis
    print("=== Global Analysis ===")
    feature_night_activity(transactions_df)

    # Test individual partner analysis
    sample_partner = transactions_df['partner_id'].value_counts().index[0]
    print(f"\n=== Individual Analysis: {sample_partner} ===")
    feature_night_activity(transactions_df, partner_id=sample_partner)
