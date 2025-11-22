"""
AML Feature: Ephemeral Account Detection
"""

import pandas as pd
import numpy as np


def feature_ephemeral_account(transactions_df, accounts_df, partner_id=None):
    """
    Detect ephemeral accounts (short-lived accounts).

    Identifies accounts that were opened and closed (or became inactive)
    within a short time period, which may indicate suspicious activity.

    Parameters:
    -----------
    transactions_df : pd.DataFrame
        Transaction data
    accounts_df : pd.DataFrame
        Account data
    partner_id : str, optional
        Specific partner to analyze
    """
    if partner_id:
        # Find accounts for this partner
        partner_txs = transactions_df[transactions_df['partner_id'] == partner_id]
        account_ids = partner_txs['account_id'].unique()
        accts = accounts_df[accounts_df['account_id'].isin(account_ids)]
        label = f"Partner {partner_id}"
    else:
        accts = accounts_df.copy()
        label = "All accounts"

    if len(accts) == 0:
        print(f"Feature: Ephemeral Account – {label} – No accounts found")
        return

    # Merge with transactions to get last transaction date
    last_tx = transactions_df.groupby('account_id')['Date'].max().reset_index()
    last_tx.columns = ['account_id', 'last_transaction_date']

    accts = accts.merge(last_tx, on='account_id', how='left')

    # Calculate account lifetime
    today = pd.Timestamp.now()

    def calc_lifetime(row):
        open_date = row['account_open_date']
        if pd.isna(open_date):
            return np.nan

        # Use close date, last tx date, or today
        if pd.notna(row['account_close_date']):
            end_date = row['account_close_date']
        elif pd.notna(row['last_transaction_date']):
            end_date = row['last_transaction_date']
        else:
            end_date = today

        return (end_date - open_date).days

    accts['lifetime_days'] = accts.apply(calc_lifetime, axis=1)

    # Ephemeral: lifetime < 90 days
    ephemeral = accts[accts['lifetime_days'] < 90]
    ephemeral_count = len(ephemeral)
    ephemeral_pct = (ephemeral_count / len(accts)) * 100 if len(accts) > 0 else 0

    avg_lifetime = accts['lifetime_days'].mean()

    # Risk assessment
    if ephemeral_pct > 30:
        risk = "HIGH"
    elif ephemeral_pct > 10:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    print(f"Feature: Ephemeral Account – {label}")
    print(f"  Total accounts: {len(accts)}")
    print(f"  Ephemeral accounts (<90 days): {ephemeral_count} ({ephemeral_pct:.1f}%)")
    print(f"  Average account lifetime: {avg_lifetime:.0f} days")
    print(f"  Risk: {risk}")
    print()


if __name__ == '__main__':
    from aml_utils import load_data

    # Load data
    transactions_df, accounts_df = load_data()

    # Test global analysis
    print("=== Global Analysis ===")
    feature_ephemeral_account(transactions_df, accounts_df)

    # Test individual partner analysis
    sample_partner = transactions_df['partner_id'].value_counts().index[0]
    print(f"\n=== Individual Analysis: {sample_partner} ===")
    feature_ephemeral_account(transactions_df, accounts_df, partner_id=sample_partner)
