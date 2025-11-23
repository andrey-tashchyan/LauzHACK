"""
AML Feature: Night-Time Activity Analysis
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


def feature_night_activity(transactions_df, partner_id=None, return_data=True):
    """
    Analyze transactions occurring during night hours.

    Computes the proportion of transactions executed between
    22:00 and 06:00, which may indicate suspicious activity.

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
        print(f"Feature: Night Activity – {label} – No transactions found")
        if return_data:
            return {
                "feature_name": "night_activity",
                "partner_id": partner_id if partner_id else "global",
                "partner_name": None,
                "metrics": {
                    "total_transactions": 0,
                    "night_count": 0,
                    "night_pct": 0,
                    "peak_hour": None
                },
                "risk_level": "LOW",
                "risk_score": 0,
                "risk_reasons": ["No transactions found"],
                "timestamp": datetime.now().isoformat()
            }
        return None

    # Extract hour
    df['hour'] = df['Date'].dt.hour

    # Night hours: 22:00 to 06:00
    night_mask = (df['hour'] >= 22) | (df['hour'] < 6)
    night_count = night_mask.sum()
    total_tx = len(df)
    night_pct = (night_count / total_tx) * 100

    # Hour distribution
    hour_dist = df['hour'].value_counts().sort_index()
    peak_hour = hour_dist.idxmax() if len(hour_dist) > 0 else None
    peak_hour_count = hour_dist.max() if len(hour_dist) > 0 else 0

    # Weekend activity (Saturday=5, Sunday=6)
    df['day_of_week'] = df['Date'].dt.dayofweek
    weekend_mask = df['day_of_week'].isin([5, 6])
    weekend_count = weekend_mask.sum()
    weekend_pct = (weekend_count / total_tx) * 100

    # Combined risk: night + weekend
    night_weekend_mask = night_mask & weekend_mask
    night_weekend_count = night_weekend_mask.sum()

    # Risk assessment
    risk_reasons = []
    if night_pct > 30 or night_weekend_count > 10:
        risk = "HIGH"
        risk_score = 85
        if night_pct > 30:
            risk_reasons.append(f"High proportion of night transactions ({night_pct:.1f}%), unusual for legitimate business")
        if night_weekend_count > 10:
            risk_reasons.append(f"{night_weekend_count} transactions during night hours on weekends")
        if peak_hour is not None and (peak_hour >= 22 or peak_hour < 6):
            risk_reasons.append(f"Peak activity at {peak_hour}:00 (night hours)")
    elif night_pct > 10 or night_weekend_count > 3:
        risk = "MEDIUM"
        risk_score = 50
        if night_pct > 10:
            risk_reasons.append(f"Moderate night activity ({night_pct:.1f}%)")
        if night_weekend_count > 3:
            risk_reasons.append(f"{night_weekend_count} transactions during night hours on weekends")
    else:
        risk = "LOW"
        risk_score = 15
        risk_reasons.append(f"Low night activity ({night_pct:.1f}%), consistent with normal business hours")

    print(f"Feature: Night Activity – {label}")
    print(f"  Total transactions: {total_tx}")
    print(f"  Night transactions (22:00-06:00): {night_count} ({night_pct:.1f}%)")
    print(f"  Weekend transactions: {weekend_count} ({weekend_pct:.1f}%)")
    print(f"  Night + weekend transactions: {night_weekend_count}")
    if peak_hour is not None:
        print(f"  Peak hour: {peak_hour}:00 ({peak_hour_count} tx)")
    print(f"  Risk: {risk} (score: {risk_score}/100)")
    if risk_reasons:
        print(f"  Reasons: {'; '.join(risk_reasons)}")
    print()

    # Return structured data
    if return_data:
        return {
            "feature_name": "night_activity",
            "partner_id": partner_id if partner_id else "global",
            "partner_name": None,
            "metrics": {
                "total_transactions": int(total_tx),
                "night_count": int(night_count),
                "night_pct": round(float(night_pct), 2),
                "weekend_count": int(weekend_count),
                "weekend_pct": round(float(weekend_pct), 2),
                "night_weekend_count": int(night_weekend_count),
                "peak_hour": int(peak_hour) if peak_hour is not None else None,
                "peak_hour_count": int(peak_hour_count)
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
    result = feature_night_activity(transactions_df, return_data=True)

    # Test individual partner analysis
    if 'partner_id_incoming' in transactions_df.columns:
        sample_partners = pd.concat([
            transactions_df['partner_id_incoming'].dropna(),
            transactions_df['partner_id_outgoing'].dropna()
        ]).value_counts()

        if len(sample_partners) > 0:
            sample_partner = sample_partners.index[0]
            print(f"\n=== Individual Analysis: {sample_partner} ===")
            result = feature_night_activity(transactions_df, partner_id=sample_partner, return_data=True)
