"""
AML Feature: Cross-Border Transaction Analysis
"""

import pandas as pd


def feature_cross_border(transactions_df, partner_id=None):
    """
    Analyze cross-border transaction patterns.

    Computes ratio of international vs domestic transactions and
    identifies transactions with high-risk countries.

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
        print(f"Feature: Cross-Border – {label} – No transactions found")
        return

    # Identify cross-border transactions
    total_tx = len(df)
    cross_border = df['ext_counterparty_country'].notna()
    cross_border_count = cross_border.sum()
    cross_border_pct = (cross_border_count / total_tx) * 100

    # High-risk countries (example list - expand as needed)
    high_risk_countries = ['Panama', 'China', 'Iran', 'North Korea', 'Syria',
                          'Afghanistan', 'Yemen', 'Myanmar']

    high_risk_tx = df[df['ext_counterparty_country'].isin(high_risk_countries)]
    high_risk_count = len(high_risk_tx)

    # Unique countries
    unique_countries = df['ext_counterparty_country'].dropna().nunique()

    # Risk assessment
    if cross_border_pct > 50 or high_risk_count > 5:
        risk = "HIGH"
    elif cross_border_pct > 20 or high_risk_count > 0:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    print(f"Feature: Cross-Border – {label}")
    print(f"  Total transactions: {total_tx}")
    print(f"  Cross-border: {cross_border_count} ({cross_border_pct:.1f}%)")
    print(f"  Unique countries: {unique_countries}")
    print(f"  High-risk country transactions: {high_risk_count}")
    print(f"  Risk: {risk}")
    print()


if __name__ == '__main__':
    from aml_utils import load_data

    # Load data
    transactions_df, accounts_df = load_data()

    # Test global analysis
    print("=== Global Analysis ===")
    feature_cross_border(transactions_df)

    # Test individual partner analysis
    sample_partner = transactions_df['partner_id'].value_counts().index[0]
    print(f"\n=== Individual Analysis: {sample_partner} ===")
    feature_cross_border(transactions_df, partner_id=sample_partner)
