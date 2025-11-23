"""
AML Feature: Irregularity Score Analysis
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


def feature_irregularity(transactions_df, partner_id=None, return_data=True):
    """
    Compute irregularity score based on transaction patterns.

    Analyzes variance in amounts, timing irregularity, and pattern breaks.

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
        print(f"Feature: Irregularity – {label} – No transactions found")
        if return_data:
            return {
                "feature_name": "irregularity",
                "partner_id": partner_id if partner_id else "global",
                "partner_name": None,
                "metrics": {
                    "total_transactions": 0,
                    "cv_amount": 0,
                    "cv_timing": 0,
                    "day_entropy": 0,
                    "irregularity_score": 0
                },
                "risk_level": "LOW",
                "risk_score": 0,
                "risk_reasons": ["No transactions found"],
                "timestamp": datetime.now().isoformat()
            }
        return None

    # Sort by date
    df = df.sort_values('Date')

    # Amount variance (coefficient of variation)
    amounts = df['Amount'].abs()
    mean_amt = amounts.mean()
    std_amt = amounts.std()
    cv_amount = (std_amt / mean_amt) if mean_amt > 0 else 0

    # Timing irregularity: variance in time between transactions
    if len(df) > 1:
        df['time_diff'] = df['Date'].diff().dt.total_seconds() / 3600  # hours
        time_diffs = df['time_diff'].dropna()
        mean_time = time_diffs.mean()
        std_time = time_diffs.std()
        cv_timing = (std_time / mean_time) if mean_time > 0 else 0
    else:
        cv_timing = 0

    # Day of week variance (entropy)
    df['day_of_week'] = df['Date'].dt.dayofweek
    day_distribution = df['day_of_week'].value_counts()
    day_probs = day_distribution / len(df)
    day_entropy = -(day_probs * np.log(day_probs + 1e-10)).sum()

    # Hour of day variance (entropy)
    df['hour_of_day'] = df['Date'].dt.hour
    hour_distribution = df['hour_of_day'].value_counts()
    hour_probs = hour_distribution / len(df)
    hour_entropy = -(hour_probs * np.log(hour_probs + 1e-10)).sum()

    # Composite irregularity score (normalized 0-100)
    # Higher CV = more irregular, Higher entropy = more spread out (could be irregular)
    irregularity_score = min(100, (cv_amount * 20 + cv_timing * 10 + day_entropy * 10 + hour_entropy * 5))

    # Risk assessment
    risk_reasons = []
    if irregularity_score > 60:
        risk = "HIGH"
        risk_score = 85
        risk_reasons.append(f"High irregularity score ({irregularity_score:.1f}/100) indicates erratic transaction patterns")
        if cv_amount > 2:
            risk_reasons.append(f"Highly variable transaction amounts (CV: {cv_amount:.2f})")
        if cv_timing > 3:
            risk_reasons.append(f"Highly irregular transaction timing (CV: {cv_timing:.2f})")
    elif irregularity_score > 30:
        risk = "MEDIUM"
        risk_score = 50
        risk_reasons.append(f"Moderate irregularity score ({irregularity_score:.1f}/100)")
        if cv_amount > 1:
            risk_reasons.append(f"Variable transaction amounts (CV: {cv_amount:.2f})")
    else:
        risk = "LOW"
        risk_score = 20
        risk_reasons.append(f"Low irregularity score ({irregularity_score:.1f}/100) indicates consistent transaction patterns")

    print(f"Feature: Irregularity – {label}")
    print(f"  Total transactions: {len(df)}")
    print(f"  Amount irregularity (CV): {cv_amount:.2f}")
    print(f"  Timing irregularity (CV): {cv_timing:.2f}")
    print(f"  Day distribution entropy: {day_entropy:.2f}")
    print(f"  Hour distribution entropy: {hour_entropy:.2f}")
    print(f"  Composite irregularity score: {irregularity_score:.1f}/100")
    print(f"  Risk: {risk} (score: {risk_score}/100)")
    if risk_reasons:
        print(f"  Reasons: {'; '.join(risk_reasons)}")
    print()

    # Return structured data
    if return_data:
        return {
            "feature_name": "irregularity",
            "partner_id": partner_id if partner_id else "global",
            "partner_name": None,
            "metrics": {
                "total_transactions": len(df),
                "cv_amount": round(float(cv_amount), 3),
                "cv_timing": round(float(cv_timing), 3),
                "day_entropy": round(float(day_entropy), 3),
                "hour_entropy": round(float(hour_entropy), 3),
                "irregularity_score": round(float(irregularity_score), 2)
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
    result = feature_irregularity(transactions_df, return_data=True)

    # Test individual partner analysis
    if 'partner_id_incoming' in transactions_df.columns:
        sample_partners = pd.concat([
            transactions_df['partner_id_incoming'].dropna(),
            transactions_df['partner_id_outgoing'].dropna()
        ]).value_counts()

        if len(sample_partners) > 0:
            sample_partner = sample_partners.index[0]
            print(f"\n=== Individual Analysis: {sample_partner} ===")
            result = feature_irregularity(transactions_df, partner_id=sample_partner, return_data=True)
