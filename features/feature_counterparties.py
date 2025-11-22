"""
AML Feature: Counterparty Analysis
"""

import pandas as pd


def feature_counterparties(transactions_df, partner_id=None):
    """
    Analyze counterparty diversity and concentration.

    Examines the number of unique counterparties and whether
    transactions are concentrated with a few counterparties.

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
        print(f"Feature: Counterparties – {label} – No transactions found")
        return

    total_tx = len(df)

    # Count unique counterparties (using counterparty_account_id)
    # Combine internal and external counterparties
    counterparties = pd.concat([
        df['counterparty_account_id'].dropna(),
        df['ext_counterparty_account_id'].dropna()
    ])
    unique_counterparties = counterparties.nunique() if len(counterparties) > 0 else 0

    # Concentration: top counterparty share
    counterparty_counts = counterparties.value_counts() if len(counterparties) > 0 else pd.Series()
    top_counterparty_pct = (counterparty_counts.iloc[0] / total_tx * 100) if len(counterparty_counts) > 0 else 0
    top_3_pct = (counterparty_counts.head(3).sum() / total_tx * 100) if len(counterparty_counts) >= 3 else 100

    # Diversity ratio
    diversity_ratio = unique_counterparties / total_tx if total_tx > 0 else 0

    # Risk assessment
    if unique_counterparties < 3 or top_counterparty_pct > 80:
        risk = "HIGH"
    elif unique_counterparties < 10 or top_counterparty_pct > 50:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    print(f"Feature: Counterparties – {label}")
    print(f"  Total transactions: {total_tx}")
    print(f"  Unique counterparties: {unique_counterparties}")
    print(f"  Diversity ratio: {diversity_ratio:.3f}")
    print(f"  Top counterparty share: {top_counterparty_pct:.1f}%")
    print(f"  Top 3 counterparties share: {top_3_pct:.1f}%")
    print(f"  Risk: {risk}")
    print()


if __name__ == '__main__':
    from aml_utils import load_data

    # Load data
    transactions_df, accounts_df = load_data()

    # Test global analysis
    print("=== Global Analysis ===")
    feature_counterparties(transactions_df)

    # Test individual partner analysis
    sample_partner = transactions_df['partner_id'].value_counts().index[0]
    print(f"\n=== Individual Analysis: {sample_partner} ===")
    feature_counterparties(transactions_df, partner_id=sample_partner)
