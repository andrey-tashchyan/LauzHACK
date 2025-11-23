"""
AML Feature: Counterparty Analysis
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

    df['counterparty_id'] = np.where(
        df['Debit/Credit'] == 'debit',
        df['partner_id_incoming'],
        df['partner_id_outgoing']
    )

    df['counterparty_account_id'] = np.where(
        df['Debit/Credit'] == 'debit',
        df['account_id_incoming'],
        df['account_id_outgoing']
    )

    df['counterparty_country'] = np.where(
        df['Debit/Credit'] == 'debit',
        df['country_name_incoming'],
        df['country_name_outgoing']
    )

    df['counterparty_sector'] = np.where(
        df['Debit/Credit'] == 'debit',
        df['industry_gic2_code_incoming'],
        df['industry_gic2_code_outgoing']
    )

    # Handle external counterparty fields
    if 'ext_counterparty_Account_ID' in df.columns:
        df['counterparty_account_id'] = df['counterparty_account_id'].fillna(df['ext_counterparty_Account_ID'])
    if 'ext_counterparty_country' in df.columns:
        df['counterparty_country'] = df['counterparty_country'].fillna(df['ext_counterparty_country'])

    # Filter by partner_id if specified
    if partner_id:
        df = df[df['logical_partner_id'] == partner_id]

    return df


def feature_counterparties(transactions_df, partner_id=None, return_data=True):
    """
    Analyze counterparty diversity and concentration.

    Examines the number of unique counterparties and whether
    transactions are concentrated with a few counterparties.

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
        print(f"Feature: Counterparties – {label} – No transactions found")
        if return_data:
            return {
                "feature_name": "counterparties",
                "partner_id": partner_id if partner_id else "global",
                "partner_name": None,
                "metrics": {
                    "total_transactions": 0,
                    "unique_counterparties": 0,
                    "diversity_ratio": 0,
                    "top_counterparty_pct": 0,
                    "top_3_pct": 0
                },
                "risk_level": "LOW",
                "risk_score": 0,
                "risk_reasons": ["No transactions found"],
                "timestamp": datetime.now().isoformat()
            }
        return None

    total_tx = len(df)

    # Count unique counterparties (using both partner_id and account_id)
    # Prioritize partner_id, fallback to account_id
    counterparties_partner = df['counterparty_id'].dropna()
    counterparties_account = df['counterparty_account_id'].dropna()

    # Combine and count unique
    if len(counterparties_partner) > 0:
        counterparties = counterparties_partner
        unique_counterparties = counterparties.nunique()
    elif len(counterparties_account) > 0:
        counterparties = counterparties_account
        unique_counterparties = counterparties.nunique()
    else:
        counterparties = pd.Series()
        unique_counterparties = 0

    # Concentration: top counterparty share
    if len(counterparties) > 0:
        counterparty_counts = counterparties.value_counts()
        top_counterparty_pct = (counterparty_counts.iloc[0] / total_tx * 100) if len(counterparty_counts) > 0 else 0
        top_3_pct = (counterparty_counts.head(3).sum() / total_tx * 100) if len(counterparty_counts) >= 3 else (counterparty_counts.sum() / total_tx * 100)
    else:
        top_counterparty_pct = 0
        top_3_pct = 0

    # Diversity ratio
    diversity_ratio = unique_counterparties / total_tx if total_tx > 0 else 0

    # Analyze high-risk counterparties (e.g., in high-risk countries)
    high_risk_countries = [
        'Panama', 'China', 'Iran', 'North Korea', 'Syria', 'Afghanistan', 'Yemen', 'Myanmar',
        'Pakistan', 'Turkey', 'Uganda', 'South Sudan', 'Senegal', 'Nigeria', 'Mali'
    ]
    high_risk_counterparties = df[df['counterparty_country'].isin(high_risk_countries)]
    high_risk_cp_count = len(high_risk_counterparties)

    # Risk assessment
    risk_reasons = []
    if unique_counterparties < 3 or top_counterparty_pct > 80:
        risk = "HIGH"
        risk_score = 85
        if unique_counterparties < 3:
            risk_reasons.append(f"Very low counterparty diversity: only {unique_counterparties} unique counterparties")
        if top_counterparty_pct > 80:
            risk_reasons.append(f"Extreme concentration: top counterparty accounts for {top_counterparty_pct:.1f}% of transactions")
    elif unique_counterparties < 10 or top_counterparty_pct > 50:
        risk = "MEDIUM"
        risk_score = 55
        if unique_counterparties < 10:
            risk_reasons.append(f"Low counterparty diversity: {unique_counterparties} unique counterparties")
        if top_counterparty_pct > 50:
            risk_reasons.append(f"High concentration: top counterparty accounts for {top_counterparty_pct:.1f}% of transactions")
    else:
        risk = "LOW"
        risk_score = 20
        risk_reasons.append(f"Good counterparty diversity: {unique_counterparties} unique counterparties")

    if high_risk_cp_count > 0:
        risk_reasons.append(f"{high_risk_cp_count} transactions with counterparties in high-risk countries")
        if risk == "LOW":
            risk = "MEDIUM"
            risk_score = max(risk_score, 50)

    print(f"Feature: Counterparties – {label}")
    print(f"  Total transactions: {total_tx}")
    print(f"  Unique counterparties: {unique_counterparties}")
    print(f"  Diversity ratio: {diversity_ratio:.3f}")
    print(f"  Top counterparty share: {top_counterparty_pct:.1f}%")
    print(f"  Top 3 counterparties share: {top_3_pct:.1f}%")
    if high_risk_cp_count > 0:
        print(f"  High-risk country counterparties: {high_risk_cp_count}")
    print(f"  Risk: {risk} (score: {risk_score}/100)")
    if risk_reasons:
        print(f"  Reasons: {'; '.join(risk_reasons)}")
    print()

    # Return structured data
    if return_data:
        return {
            "feature_name": "counterparties",
            "partner_id": partner_id if partner_id else "global",
            "partner_name": None,
            "metrics": {
                "total_transactions": int(total_tx),
                "unique_counterparties": int(unique_counterparties),
                "diversity_ratio": round(float(diversity_ratio), 3),
                "top_counterparty_pct": round(float(top_counterparty_pct), 2),
                "top_3_pct": round(float(top_3_pct), 2),
                "high_risk_counterparty_count": int(high_risk_cp_count)
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
    result = feature_counterparties(transactions_df, return_data=True)

    # Test individual partner analysis
    if 'partner_id_incoming' in transactions_df.columns:
        sample_partners = pd.concat([
            transactions_df['partner_id_incoming'].dropna(),
            transactions_df['partner_id_outgoing'].dropna()
        ]).value_counts()

        if len(sample_partners) > 0:
            sample_partner = sample_partners.index[0]
            print(f"\n=== Individual Analysis: {sample_partner} ===")
            result = feature_counterparties(transactions_df, partner_id=sample_partner, return_data=True)
