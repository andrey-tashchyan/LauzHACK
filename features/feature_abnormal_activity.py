"""
AML Feature: Abnormal Activity Detection
"""

import pandas as pd


def feature_abnormal_activity(transactions_df, accounts_df, partner_id=None):
    """
    Detect abnormal spikes in account activity.

    Compares recent activity to historical baseline to identify
    sudden increases in transaction volume or amounts.

    Parameters:
    -----------
    transactions_df : pd.DataFrame
        Transaction data
    accounts_df : pd.DataFrame
        Account data
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
        print(f"Feature: Abnormal Activity – {label} – No transactions found")
        return

    # Sort by date
    df = df.sort_values('Date')

    # Split into baseline (first 80%) and recent (last 20%)
    split_point = int(len(df) * 0.8)
    baseline = df.iloc[:split_point]
    recent = df.iloc[split_point:]

    if len(baseline) == 0 or len(recent) == 0:
        print(f"Feature: Abnormal Activity – {label} – Insufficient data for comparison")
        return

    # Compare transaction volume
    baseline_days = (baseline['Date'].max() - baseline['Date'].min()).days or 1
    recent_days = (recent['Date'].max() - recent['Date'].min()).days or 1

    baseline_rate = len(baseline) / baseline_days
    recent_rate = len(recent) / recent_days
    volume_increase = ((recent_rate - baseline_rate) / baseline_rate * 100) if baseline_rate > 0 else 0

    # Compare amounts
    baseline_avg_amount = baseline['Amount'].abs().mean()
    recent_avg_amount = recent['Amount'].abs().mean()
    amount_increase = ((recent_avg_amount - baseline_avg_amount) / baseline_avg_amount * 100) if baseline_avg_amount > 0 else 0

    # Risk assessment
    if volume_increase > 200 or amount_increase > 200:
        risk = "HIGH"
    elif volume_increase > 100 or amount_increase > 100:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    print(f"Feature: Abnormal Activity – {label}")
    print(f"  Baseline period: {baseline_days} days, {len(baseline)} tx")
    print(f"  Recent period: {recent_days} days, {len(recent)} tx")
    print(f"  Volume change: {volume_increase:+.1f}%")
    print(f"  Average amount change: {amount_increase:+.1f}%")
    print(f"  Risk: {risk}")
    print()


if __name__ == '__main__':
    from features.aml_utils import load_data

    # Load data
    transactions_df, accounts_df = load_data()

    # Test global analysis
    print("=== Global Analysis ===")
    feature_abnormal_activity(transactions_df, accounts_df)

    # Test individual partner analysis
    sample_partner = transactions_df['partner_id'].value_counts().index[0]
    print(f"\n=== Individual Analysis: {sample_partner} ===")
    feature_abnormal_activity(transactions_df, accounts_df, partner_id=sample_partner)
