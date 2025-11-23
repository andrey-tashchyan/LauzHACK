"""
AML Feature: Cross-Border Transaction Analysis
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

    df['logical_partner_country'] = np.where(
        df['Debit/Credit'] == 'debit',
        df['country_name_outgoing'],
        df['country_name_incoming']
    )

    df['logical_partner_country_status'] = np.where(
        df['Debit/Credit'] == 'debit',
        df['partner_country_status_code_outgoing'],
        df['partner_country_status_code_incoming']
    )

    df['counterparty_country'] = np.where(
        df['Debit/Credit'] == 'debit',
        df['country_name_incoming'],
        df['country_name_outgoing']
    )

    df['counterparty_country_status'] = np.where(
        df['Debit/Credit'] == 'debit',
        df['partner_country_status_code_incoming'],
        df['partner_country_status_code_outgoing']
    )

    # Also handle external counterparty fields
    if 'ext_counterparty_country' in df.columns:
        df['counterparty_country'] = df['counterparty_country'].fillna(df['ext_counterparty_country'])

    # Filter by partner_id if specified
    if partner_id:
        df = df[df['logical_partner_id'] == partner_id]

    return df


def feature_cross_border(transactions_df, partner_id=None, return_data=True):
    """
    Analyze cross-border transaction patterns.

    Computes ratio of international vs domestic transactions and
    identifies transactions with high-risk countries.

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
        print(f"Feature: Cross-Border – {label} – No transactions found")
        if return_data:
            return {
                "feature_name": "cross_border",
                "partner_id": partner_id if partner_id else "global",
                "partner_name": None,
                "metrics": {
                    "total_transactions": 0,
                    "cross_border_count": 0,
                    "cross_border_pct": 0,
                    "unique_countries": 0,
                    "high_risk_count": 0
                },
                "risk_level": "LOW",
                "risk_score": 0,
                "risk_reasons": ["No transactions found"],
                "timestamp": datetime.now().isoformat()
            }
        return None

    total_tx = len(df)

    # Determine home country (most common partner country)
    home_countries = df['logical_partner_country'].dropna()
    home_country = home_countries.mode()[0] if len(home_countries) > 0 else None

    # Identify cross-border transactions
    # A transaction is cross-border if counterparty country differs from partner's home country
    if home_country:
        cross_border_mask = (df['counterparty_country'].notna()) & (df['counterparty_country'] != home_country)
    else:
        # If we can't determine home country, any non-null counterparty country is cross-border
        cross_border_mask = df['counterparty_country'].notna()

    cross_border_count = cross_border_mask.sum()
    cross_border_pct = (cross_border_count / total_tx) * 100 if total_tx > 0 else 0

    # High-risk countries (FATF grey/black list and other high-risk jurisdictions)
    # This is an example list - should be updated based on current FATF recommendations
    high_risk_countries = [
        'Panama', 'China', 'Iran', 'North Korea', 'Syria', 'Afghanistan', 'Yemen', 'Myanmar',
        'Pakistan', 'Turkey', 'Uganda', 'South Sudan', 'Senegal', 'Nigeria', 'Mali',
        'Mozambique', 'Philippines', 'Venezuela', 'Haiti', 'Barbados', 'Jamaica',
        'Democratic Republic of the Congo', 'Burkina Faso', 'Cameroon', 'Croatia',
        'Tanzania', 'Vietnam', 'Albania', 'Cayman Islands', 'Jordan', 'Monaco'
    ]

    high_risk_tx = df[df['counterparty_country'].isin(high_risk_countries)]
    high_risk_count = len(high_risk_tx)
    high_risk_pct = (high_risk_count / total_tx) * 100 if total_tx > 0 else 0

    # Unique countries
    unique_countries = df['counterparty_country'].dropna().nunique()
    country_list = df['counterparty_country'].dropna().unique().tolist()

    # High-risk countries involved
    high_risk_countries_involved = sorted(set(high_risk_tx['counterparty_country'].dropna().unique()))

    # Risk assessment
    risk_reasons = []
    if cross_border_pct > 50 or high_risk_count > 5:
        risk = "HIGH"
        risk_score = 85
        if cross_border_pct > 50:
            risk_reasons.append(f"Majority of transactions are cross-border ({cross_border_pct:.1f}%)")
        if high_risk_count > 5:
            risk_reasons.append(f"{high_risk_count} transactions with high-risk countries: {', '.join(high_risk_countries_involved[:3])}")
    elif cross_border_pct > 20 or high_risk_count > 0:
        risk = "MEDIUM"
        risk_score = 55
        if cross_border_pct > 20:
            risk_reasons.append(f"Significant cross-border activity ({cross_border_pct:.1f}%)")
        if high_risk_count > 0:
            risk_reasons.append(f"{high_risk_count} transactions with high-risk countries: {', '.join(high_risk_countries_involved)}")
    else:
        risk = "LOW"
        risk_score = 15
        risk_reasons.append("Primarily domestic transactions with no high-risk jurisdictions")

    if unique_countries > 10:
        risk_reasons.append(f"High geographic diversity: {unique_countries} different countries")

    print(f"Feature: Cross-Border – {label}")
    print(f"  Total transactions: {total_tx}")
    print(f"  Home country: {home_country}")
    print(f"  Cross-border: {cross_border_count} ({cross_border_pct:.1f}%)")
    print(f"  Unique countries: {unique_countries}")
    print(f"  High-risk country transactions: {high_risk_count} ({high_risk_pct:.1f}%)")
    if high_risk_countries_involved:
        print(f"    - Countries: {', '.join(high_risk_countries_involved)}")
    print(f"  Risk: {risk} (score: {risk_score}/100)")
    if risk_reasons:
        print(f"  Reasons: {'; '.join(risk_reasons)}")
    print()

    # Return structured data
    if return_data:
        return {
            "feature_name": "cross_border",
            "partner_id": partner_id if partner_id else "global",
            "partner_name": None,
            "metrics": {
                "total_transactions": int(total_tx),
                "home_country": home_country,
                "cross_border_count": int(cross_border_count),
                "cross_border_pct": round(float(cross_border_pct), 2),
                "unique_countries": int(unique_countries),
                "countries_list": country_list[:20],  # Limit to first 20
                "high_risk_count": int(high_risk_count),
                "high_risk_pct": round(float(high_risk_pct), 2),
                "high_risk_countries_involved": high_risk_countries_involved
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
    result = feature_cross_border(transactions_df, return_data=True)

    # Test individual partner analysis
    if 'partner_id_incoming' in transactions_df.columns:
        sample_partners = pd.concat([
            transactions_df['partner_id_incoming'].dropna(),
            transactions_df['partner_id_outgoing'].dropna()
        ]).value_counts()

        if len(sample_partners) > 0:
            sample_partner = sample_partners.index[0]
            print(f"\n=== Individual Analysis: {sample_partner} ===")
            result = feature_cross_border(transactions_df, partner_id=sample_partner, return_data=True)
