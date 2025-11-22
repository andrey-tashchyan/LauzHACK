"""
AML Feature: Atypical Transaction Amounts Detection
"""

import pandas as pd


def feature_atypical_amounts(transactions_df, partner_id=None):
    """
    Detect outlier transaction amounts compared to typical patterns.

    Uses IQR (Interquartile Range) method to identify atypical amounts.

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
        print(f"Feature: Atypical Amounts – {label} – No transactions found")
        return

    # Use absolute amounts for analysis
    amounts = df['Amount'].abs()

    # IQR method
    Q1 = amounts.quantile(0.25)
    Q3 = amounts.quantile(0.75)
    IQR = Q3 - Q1

    lower_bound = Q1 - 3 * IQR
    upper_bound = Q3 + 3 * IQR

    outliers = df[(amounts < lower_bound) | (amounts > upper_bound)]
    outlier_count = len(outliers)
    outlier_pct = (outlier_count / len(df)) * 100

    # Z-score for extreme outliers
    mean_amount = amounts.mean()
    std_amount = amounts.std()
    if std_amount > 0:
        z_scores = (amounts - mean_amount) / std_amount
        extreme_outliers = (z_scores.abs() > 3).sum()
    else:
        extreme_outliers = 0

    # Risk assessment
    if outlier_pct > 10 or extreme_outliers > 5:
        risk = "HIGH"
    elif outlier_pct > 5 or extreme_outliers > 2:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    print(f"Feature: Atypical Amounts – {label}")
    print(f"  Total transactions: {len(df)}")
    print(f"  Outliers (IQR method): {outlier_count} ({outlier_pct:.1f}%)")
    print(f"  Extreme outliers (z>3): {extreme_outliers}")
    print(f"  Median amount: {amounts.median():.2f}")
    print(f"  Max amount: {amounts.max():.2f}")
    print(f"  Risk: {risk}")
    print()


if __name__ == '__main__':
    from aml_utils import load_data

    # Load data
    transactions_df, accounts_df = load_data()

    # Test global analysis
    print("=== Global Analysis ===")
    feature_atypical_amounts(transactions_df)

    # Test individual partner analysis
    sample_partner = transactions_df['partner_id'].value_counts().index[0]
    print(f"\n=== Individual Analysis: {sample_partner} ===")
    feature_atypical_amounts(transactions_df, partner_id=sample_partner)
