"""
AML Feature: Account Multiplicity Analysis
"""

import pandas as pd


def feature_account_multiplicity(accounts_df, transactions_df=None):
    """
    Analyze the number of accounts per partner.

    Identifies partners with multiple accounts, which may indicate
    attempts to evade detection limits or structure transactions.

    Parameters:
    -----------
    accounts_df : pd.DataFrame
        Account data
    transactions_df : pd.DataFrame, optional
        Transaction data to link accounts to partners
    """
    if transactions_df is None:
        print("Feature: Account Multiplicity – Requires transaction data to link accounts to partners")
        return

    # Get unique account-partner mappings
    account_partner = transactions_df[['account_id', 'partner_id']].drop_duplicates()

    # Count accounts per partner
    accounts_per_partner = account_partner.groupby('partner_id').size().reset_index(name='account_count')

    total_partners = len(accounts_per_partner)
    multi_account_partners = accounts_per_partner[accounts_per_partner['account_count'] > 1]
    multi_account_count = len(multi_account_partners)
    multi_account_pct = (multi_account_count / total_partners * 100) if total_partners > 0 else 0

    # High multiplicity: >3 accounts
    high_multi = accounts_per_partner[accounts_per_partner['account_count'] > 3]
    high_multi_count = len(high_multi)

    max_accounts = accounts_per_partner['account_count'].max()
    avg_accounts = accounts_per_partner['account_count'].mean()

    # Risk assessment
    if high_multi_count > 10 or max_accounts > 10:
        risk = "HIGH"
    elif high_multi_count > 3 or max_accounts > 5:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    print(f"Feature: Account Multiplicity – All partners")
    print(f"  Total partners: {total_partners}")
    print(f"  Partners with multiple accounts: {multi_account_count} ({multi_account_pct:.1f}%)")
    print(f"  Partners with >3 accounts: {high_multi_count}")
    print(f"  Average accounts per partner: {avg_accounts:.2f}")
    print(f"  Max accounts (single partner): {max_accounts}")
    print(f"  Risk: {risk}")
    print()

    # Show top partners with most accounts
    if len(multi_account_partners) > 0:
        top_partners = accounts_per_partner.nlargest(5, 'account_count')
        print("  Top 5 partners by account count:")
        for _, row in top_partners.iterrows():
            print(f"    Partner {row['partner_id']}: {row['account_count']} accounts")
    print()


if __name__ == '__main__':
    from features.aml_utils import load_data

    # Load data
    transactions_df, accounts_df = load_data()

    # Test analysis
    print("=== Account Multiplicity Analysis ===")
    feature_account_multiplicity(accounts_df, transactions_df)
