"""
AML Feature: Atypical Transaction Amounts Detection
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

    # Filter by partner_id if specified
    if partner_id:
        df = df[df['logical_partner_id'] == partner_id]

    return df


def feature_atypical_amounts(transactions_df, partner_id=None, return_data=True):
    """
    Detect outlier transaction amounts compared to typical patterns.

    Uses IQR (Interquartile Range) and Z-score methods to identify atypical amounts.

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
        print(f"Feature: Atypical Amounts – {label} – No transactions found")
        if return_data:
            return {
                "feature_name": "atypical_amounts",
                "partner_id": partner_id if partner_id else "global",
                "partner_name": None,
                "metrics": {
                    "total_transactions": 0,
                    "outlier_count": 0,
                    "outlier_pct": 0,
                    "extreme_outliers": 0
                },
                "risk_level": "LOW",
                "risk_score": 0,
                "risk_reasons": ["No transactions found"],
                "timestamp": datetime.now().isoformat()
            }
        return None

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

    # Additional statistics
    median_amount = amounts.median()
    max_amount = amounts.max()
    min_amount = amounts.min()

    # Risk assessment
    risk_reasons = []
    if outlier_pct > 10 or extreme_outliers > 5:
        risk = "HIGH"
        risk_score = 85
        if outlier_pct > 10:
            risk_reasons.append(f"High proportion of outlier amounts ({outlier_pct:.1f}% of transactions)")
        if extreme_outliers > 5:
            risk_reasons.append(f"{extreme_outliers} extreme outliers detected (z-score > 3)")
    elif outlier_pct > 5 or extreme_outliers > 2:
        risk = "MEDIUM"
        risk_score = 55
        if outlier_pct > 5:
            risk_reasons.append(f"Moderate outlier amounts ({outlier_pct:.1f}% of transactions)")
        if extreme_outliers > 2:
            risk_reasons.append(f"{extreme_outliers} extreme outliers detected")
    else:
        risk = "LOW"
        risk_score = 20
        risk_reasons.append("Transaction amounts follow normal distribution patterns")

    print(f"Feature: Atypical Amounts – {label}")
    print(f"  Total transactions: {len(df)}")
    print(f"  Outliers (IQR method): {outlier_count} ({outlier_pct:.1f}%)")
    print(f"  Extreme outliers (z>3): {extreme_outliers}")
    print(f"  Amount statistics:")
    print(f"    - Median: {median_amount:.2f}")
    print(f"    - Mean: {mean_amount:.2f}")
    print(f"    - Min: {min_amount:.2f}")
    print(f"    - Max: {max_amount:.2f}")
    print(f"  Risk: {risk} (score: {risk_score}/100)")
    if risk_reasons:
        print(f"  Reasons: {'; '.join(risk_reasons)}")
    print()

    # Return structured data
    if return_data:
        return {
            "feature_name": "atypical_amounts",
            "partner_id": partner_id if partner_id else "global",
            "partner_name": None,
            "metrics": {
                "total_transactions": len(df),
                "outlier_count": int(outlier_count),
                "outlier_pct": round(float(outlier_pct), 2),
                "extreme_outliers": int(extreme_outliers),
                "median_amount": round(float(median_amount), 2),
                "mean_amount": round(float(mean_amount), 2),
                "min_amount": round(float(min_amount), 2),
                "max_amount": round(float(max_amount), 2),
                "Q1": round(float(Q1), 2),
                "Q3": round(float(Q3), 2),
                "IQR": round(float(IQR), 2)
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
    result = feature_atypical_amounts(transactions_df, return_data=True)

    # Test individual partner analysis
    if 'partner_id_incoming' in transactions_df.columns:
        sample_partners = pd.concat([
            transactions_df['partner_id_incoming'].dropna(),
            transactions_df['partner_id_outgoing'].dropna()
        ]).value_counts()

        if len(sample_partners) > 0:
            sample_partner = sample_partners.index[0]
            print(f"\n=== Individual Analysis: {sample_partner} ===")
            result = feature_atypical_amounts(transactions_df, partner_id=sample_partner, return_data=True)
