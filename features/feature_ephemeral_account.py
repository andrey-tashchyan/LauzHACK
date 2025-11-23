"""
AML Feature: Ephemeral Account Detection
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

    df['logical_account_id'] = np.where(
        df['Debit/Credit'] == 'debit',
        df['account_id_outgoing'],
        df['account_id_incoming']
    )

    df['logical_account_open_date'] = np.where(
        df['Debit/Credit'] == 'debit',
        df['account_open_date_outgoing'],
        df['account_open_date_incoming']
    )

    df['logical_account_close_date'] = np.where(
        df['Debit/Credit'] == 'debit',
        df['account_close_date_outgoing'],
        df['account_close_date_incoming']
    )

    # Convert account dates to datetime
    df['logical_account_open_date'] = pd.to_datetime(df['logical_account_open_date'], errors='coerce')
    df['logical_account_close_date'] = pd.to_datetime(df['logical_account_close_date'], errors='coerce')

    # Filter by partner_id if specified
    if partner_id:
        df = df[df['logical_partner_id'] == partner_id]

    return df


def feature_ephemeral_account(transactions_df, partner_id=None, return_data=True):
    """
    Detect ephemeral accounts (short-lived accounts).

    Identifies accounts that were opened and closed (or became inactive)
    within a short time period, which may indicate suspicious activity.

    This version is adapted for the new transaction schema with incoming/outgoing structure.
    Note: Unlike the old version, this doesn't require a separate accounts_df - all account
    information is derived from the transaction data itself.

    Parameters:
    -----------
    transactions_df : pd.DataFrame
        Transaction data with new schema (includes Debit/Credit, incoming/outgoing fields,
        and account open/close dates)
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
        label = "All accounts"

    if len(df) == 0:
        print(f"Feature: Ephemeral Account – {label} – No transactions found")
        if return_data:
            return {
                "feature_name": "ephemeral_account",
                "partner_id": partner_id if partner_id else "global",
                "partner_name": None,
                "metrics": {
                    "total_accounts": 0,
                    "ephemeral_count": 0,
                    "ephemeral_pct": 0,
                    "avg_lifetime_days": 0
                },
                "risk_level": "LOW",
                "risk_score": 0,
                "risk_reasons": ["No transactions found"],
                "timestamp": datetime.now().isoformat()
            }
        return None

    # Get unique accounts with their metadata
    account_data = df.groupby('logical_account_id').agg({
        'logical_account_open_date': 'first',
        'logical_account_close_date': 'first',
        'Date': ['min', 'max', 'count']
    }).reset_index()

    account_data.columns = ['account_id', 'open_date', 'close_date', 'first_tx_date', 'last_tx_date', 'tx_count']

    # Calculate account lifetime
    today = pd.Timestamp.now()

    def calc_lifetime(row):
        open_date = row['open_date']
        if pd.isna(open_date):
            # If no open date, use first transaction date
            open_date = row['first_tx_date']

        if pd.isna(open_date):
            return np.nan

        # Use close date, last tx date, or today
        if pd.notna(row['close_date']):
            end_date = row['close_date']
        elif pd.notna(row['last_tx_date']):
            end_date = row['last_tx_date']
        else:
            end_date = today

        return (end_date - open_date).days

    account_data['lifetime_days'] = account_data.apply(calc_lifetime, axis=1)

    # Remove accounts with invalid lifetime
    valid_accounts = account_data[account_data['lifetime_days'].notna()].copy()

    if len(valid_accounts) == 0:
        print(f"Feature: Ephemeral Account – {label} – No valid account lifetime data")
        if return_data:
            return {
                "feature_name": "ephemeral_account",
                "partner_id": partner_id if partner_id else "global",
                "partner_name": None,
                "metrics": {
                    "total_accounts": 0,
                    "ephemeral_count": 0,
                    "ephemeral_pct": 0,
                    "avg_lifetime_days": 0
                },
                "risk_level": "LOW",
                "risk_score": 0,
                "risk_reasons": ["No valid account lifetime data"],
                "timestamp": datetime.now().isoformat()
            }
        return None

    # Ephemeral: lifetime < 90 days
    ephemeral = valid_accounts[valid_accounts['lifetime_days'] < 90]
    ephemeral_count = len(ephemeral)
    ephemeral_pct = (ephemeral_count / len(valid_accounts)) * 100

    # Very ephemeral: lifetime < 30 days
    very_ephemeral = valid_accounts[valid_accounts['lifetime_days'] < 30]
    very_ephemeral_count = len(very_ephemeral)

    # High activity ephemeral accounts (short-lived but many transactions)
    high_activity_ephemeral = ephemeral[ephemeral['tx_count'] > 10]
    high_activity_count = len(high_activity_ephemeral)

    avg_lifetime = valid_accounts['lifetime_days'].mean()
    median_lifetime = valid_accounts['lifetime_days'].median()

    # Risk assessment
    risk_reasons = []
    if ephemeral_pct > 30 or high_activity_count > 3:
        risk = "HIGH"
        risk_score = 85
        if ephemeral_pct > 30:
            risk_reasons.append(f"High proportion of ephemeral accounts ({ephemeral_pct:.1f}% with <90 day lifetime)")
        if very_ephemeral_count > 0:
            risk_reasons.append(f"{very_ephemeral_count} very short-lived accounts (<30 days)")
        if high_activity_count > 3:
            risk_reasons.append(f"{high_activity_count} ephemeral accounts with high transaction volume")
    elif ephemeral_pct > 10 or high_activity_count > 0:
        risk = "MEDIUM"
        risk_score = 55
        if ephemeral_pct > 10:
            risk_reasons.append(f"Moderate ephemeral accounts ({ephemeral_pct:.1f}% with <90 day lifetime)")
        if high_activity_count > 0:
            risk_reasons.append(f"{high_activity_count} ephemeral accounts with high transaction volume")
    else:
        risk = "LOW"
        risk_score = 15
        risk_reasons.append(f"Low proportion of ephemeral accounts ({ephemeral_pct:.1f}%)")

    print(f"Feature: Ephemeral Account – {label}")
    print(f"  Total accounts: {len(valid_accounts)}")
    print(f"  Ephemeral accounts (<90 days): {ephemeral_count} ({ephemeral_pct:.1f}%)")
    print(f"  Very ephemeral (<30 days): {very_ephemeral_count}")
    print(f"  High-activity ephemeral: {high_activity_count}")
    print(f"  Average account lifetime: {avg_lifetime:.0f} days")
    print(f"  Median account lifetime: {median_lifetime:.0f} days")
    print(f"  Risk: {risk} (score: {risk_score}/100)")
    if risk_reasons:
        print(f"  Reasons: {'; '.join(risk_reasons)}")
    print()

    # Return structured data
    if return_data:
        return {
            "feature_name": "ephemeral_account",
            "partner_id": partner_id if partner_id else "global",
            "partner_name": None,
            "metrics": {
                "total_accounts": int(len(valid_accounts)),
                "ephemeral_count": int(ephemeral_count),
                "ephemeral_pct": round(float(ephemeral_pct), 2),
                "very_ephemeral_count": int(very_ephemeral_count),
                "high_activity_ephemeral_count": int(high_activity_count),
                "avg_lifetime_days": round(float(avg_lifetime), 1),
                "median_lifetime_days": round(float(median_lifetime), 1)
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
    result = feature_ephemeral_account(transactions_df, return_data=True)

    # Test individual partner analysis
    if 'partner_id_incoming' in transactions_df.columns:
        sample_partners = pd.concat([
            transactions_df['partner_id_incoming'].dropna(),
            transactions_df['partner_id_outgoing'].dropna()
        ]).value_counts()

        if len(sample_partners) > 0:
            sample_partner = sample_partners.index[0]
            print(f"\n=== Individual Analysis: {sample_partner} ===")
            result = feature_ephemeral_account(transactions_df, partner_id=sample_partner, return_data=True)
