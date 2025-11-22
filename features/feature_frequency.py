"""
AML Feature: Transaction Frequency Analysis
"""

import pandas as pd
from datetime import datetime


def feature_frequency(transactions_df, partner_id=None, return_data=True):
    """
    Analyze transaction frequency over time.

    Computes the number of transactions per day/week and identifies
    patterns that may indicate suspicious activity.

    Parameters:
    -----------
    transactions_df : pd.DataFrame
        Transaction data
    partner_id : str, optional
        Specific partner to analyze. If None, analyzes all transactions.
    """
    df = transactions_df.copy()

    # Filter by partner if specified
    if partner_id:
        df = df[df['partner_id'] == partner_id]
        label = f"Partner {partner_id}"
    else:
        label = "All partners"

    if len(df) == 0:
        print(f"Feature: Frequency – {label} – No transactions found")
        return None if return_data else None

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
    print(f"  Risk: {risk}")
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
    from aml_utils import load_data

    # Load data
    transactions_df, accounts_df = load_data()

    # Test global analysis
    print("=== Global Analysis ===")
    feature_frequency(transactions_df)

    # Test individual partner analysis
    sample_partner = transactions_df['partner_id'].value_counts().index[0]
    print(f"\n=== Individual Analysis: {sample_partner} ===")
    feature_frequency(transactions_df, partner_id=sample_partner)
