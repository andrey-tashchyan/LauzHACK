"""
AML Feature: Account Age Analysis
"""

import pandas as pd
import numpy as np


def feature_account_age(accounts_df, partner_id=None):
    """
    Analyze account age distribution.

    Computes the age in months of each account from opening to
    closing or to today if still open.

    Parameters:
    -----------
    accounts_df : pd.DataFrame
        Account data
    partner_id : str, optional
        Specific partner to analyze
    """
    accts = accounts_df.copy()

    if partner_id:
        # This would require a partner-account mapping
        # For now, we'll analyze all accounts
        label = f"Partner {partner_id} (all accounts shown)"
    else:
        label = "All accounts"

    if len(accts) == 0:
        print(f"Feature: Account Age – {label} – No accounts found")
        return

    # Calculate age in months
    today = pd.Timestamp.now()

    def calc_age_months(row):
        open_date = row['account_open_date']
        if pd.isna(open_date):
            return np.nan

        if pd.notna(row['account_close_date']):
            end_date = row['account_close_date']
        else:
            end_date = today

        return (end_date - open_date).days / 30.44

    accts['age_months'] = accts.apply(calc_age_months, axis=1)

    # Statistics
    mean_age = accts['age_months'].mean()
    median_age = accts['age_months'].median()
    min_age = accts['age_months'].min()
    max_age = accts['age_months'].max()

    # New accounts (<6 months)
    new_accounts = (accts['age_months'] < 6).sum()
    new_accounts_pct = (new_accounts / len(accts)) * 100

    # Risk assessment
    if new_accounts_pct > 40:
        risk = "HIGH"
    elif new_accounts_pct > 20:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    print(f"Feature: Account Age – {label}")
    print(f"  Total accounts: {len(accts)}")
    print(f"  Average age: {mean_age:.1f} months")
    print(f"  Median age: {median_age:.1f} months")
    print(f"  Range: {min_age:.1f} - {max_age:.1f} months")
    print(f"  New accounts (<6 months): {new_accounts} ({new_accounts_pct:.1f}%)")
    print(f"  Risk: {risk}")
    print()


if __name__ == '__main__':
    from features.aml_utils import load_data

    # Load data
    transactions_df, accounts_df = load_data()

    # Test analysis
    print("=== Account Age Analysis ===")
    feature_account_age(accounts_df)
