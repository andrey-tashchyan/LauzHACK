"""
AML Feature Analysis - Run All Features

This script runs all AML features on the dataset.
"""

from aml_utils import load_data
from features.feature_frequency import feature_frequency
from features.feature_burst_structuring import feature_burst_structuring
from features.feature_atypical_amounts import feature_atypical_amounts
from features.feature_cross_border import feature_cross_border
from features.feature_counterparties import feature_counterparties
from features.feature_irregularity import feature_irregularity
from features.feature_night_activity import feature_night_activity
from features.feature_ephemeral_account import feature_ephemeral_account
from features.feature_account_age import feature_account_age
from features.feature_abnormal_activity import feature_abnormal_activity
from features.feature_account_multiplicity import feature_account_multiplicity


def run_all_features(transactions_df, accounts_df, partner_id=None, partner_name=None, save_json=True):
    """
    Run all AML features on the dataset.

    Parameters:
    -----------
    transactions_df : pd.DataFrame
        Transaction data
    accounts_df : pd.DataFrame
        Account data
    partner_id : str, optional
        Specific partner to analyze. If None, analyzes all data.
    partner_name : str, optional
        Partner name for reporting
    save_json : bool, optional
        Whether to save results to JSON file

    Returns:
    --------
    dict
        All feature results in structured format
    """
    import json
    from datetime import datetime

    if partner_id:
        print(f"\n{'='*70}")
        print(f"AML ANALYSIS FOR PARTNER: {partner_id}")
        if partner_name:
            print(f"NAME: {partner_name}")
        print(f"{'='*70}\n")
    else:
        print(f"\n{'='*70}")
        print(f"GLOBAL AML ANALYSIS")
        print(f"{'='*70}\n")

    # Collect all results
    results = []

    # Transaction behavior features
    result = feature_frequency(transactions_df, partner_id)
    if result:
        result['partner_name'] = partner_name
        results.append(result)

    result = feature_burst_structuring(transactions_df, partner_id)
    if result:
        result['partner_name'] = partner_name
        results.append(result)

    result = feature_atypical_amounts(transactions_df, partner_id)
    if result:
        result['partner_name'] = partner_name
        results.append(result)

    result = feature_cross_border(transactions_df, partner_id)
    if result:
        result['partner_name'] = partner_name
        results.append(result)

    result = feature_counterparties(transactions_df, partner_id)
    if result:
        result['partner_name'] = partner_name
        results.append(result)

    result = feature_irregularity(transactions_df, partner_id)
    if result:
        result['partner_name'] = partner_name
        results.append(result)

    result = feature_night_activity(transactions_df, partner_id)
    if result:
        result['partner_name'] = partner_name
        results.append(result)

    # Account features
    result = feature_ephemeral_account(transactions_df, accounts_df, partner_id)
    if result:
        result['partner_name'] = partner_name
        results.append(result)

    result = feature_abnormal_activity(transactions_df, accounts_df, partner_id)
    if result:
        result['partner_name'] = partner_name
        results.append(result)

    # Account age (no partner_id filtering)
    if not partner_id:
        result = feature_account_age(accounts_df)
        if result:
            results.append(result)
        result = feature_account_multiplicity(accounts_df, transactions_df)
        if result:
            results.append(result)

    # Create comprehensive report
    analysis_report = {
        "analysis_metadata": {
            "partner_id": partner_id if partner_id else "global",
            "partner_name": partner_name,
            "analysis_timestamp": datetime.now().isoformat(),
            "total_features_analyzed": len(results)
        },
        "features": results,
        "summary": {
            "high_risk_features": len([r for r in results if r.get('risk_level') == 'HIGH']),
            "medium_risk_features": len([r for r in results if r.get('risk_level') == 'MEDIUM']),
            "low_risk_features": len([r for r in results if r.get('risk_level') == 'LOW']),
            "average_risk_score": round(sum([r.get('risk_score', 0) for r in results]) / len(results), 2) if results else 0
        }
    }

    # Save to JSON if requested
    if save_json and partner_id:
        import os

        # Create json_files directory if it doesn't exist
        os.makedirs('json_files', exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"json_files/analysis_{partner_id}_{timestamp}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(analysis_report, f, indent=2, ensure_ascii=False)
        print(f"\n📊 Analysis saved to: {filename}\n")

    return analysis_report


if __name__ == '__main__':
    import pandas as pd

    print("="*70)
    print("AML FEATURE ANALYSIS - LOADING DATA")
    print("="*70)

    # Load data
    transactions_df, accounts_df = load_data()
    print(f"\nLoaded {len(transactions_df):,} transactions")
    print(f"Loaded {len(accounts_df):,} accounts")

    # Load partner data for names and create mapping
    try:
        partners_df = pd.read_csv('LauzHACK/partner.csv')
        partner_role_df = pd.read_csv('LauzHACK/partner_role.csv')
        br_to_account_df = pd.read_csv('LauzHACK/br_to_account.csv')

        # Create mapping: account_id -> partner info
        # partner_role: partner_id -> br_id (entity_id when entity_type='BR')
        # br_to_account: br_id -> account_id
        partner_br = partner_role_df[partner_role_df['entity_type'] == 'BR'][['partner_id', 'entity_id']]
        partner_br.columns = ['partner_id', 'br_id']

        # Merge to get partner_id -> account_id mapping
        account_mapping = br_to_account_df.merge(partner_br, on='br_id', how='left')
        account_mapping = account_mapping.merge(partners_df[['partner_id', 'partner_name']], on='partner_id', how='left')

        print(f"Loaded {len(partners_df):,} partners with name mapping")
    except Exception as e:
        account_mapping = None
        print(f"Note: Could not load partner mapping ({e}), showing IDs only")

    # Show top partners by transaction count
    top_partners = transactions_df['partner_id'].value_counts().head(10)

    print(f"\n{'='*70}")
    print(f"TOP 10 ACCOUNTS BY TRANSACTION VOLUME")
    print(f"{'='*70}\n")

    for idx, (account_id, count) in enumerate(top_partners.items(), 1):
        # Get partner name if available
        if account_mapping is not None:
            partner_info = account_mapping[account_mapping['account_id'] == account_id]
            if not partner_info.empty and pd.notna(partner_info.iloc[0].get('partner_name')):
                name = partner_info.iloc[0]['partner_name']
                print(f"{idx}. {name} (Account ID: {account_id}) - {count:,} transactions")
            else:
                print(f"{idx}. Account ID: {account_id} - {count:,} transactions")
        else:
            print(f"{idx}. Account ID: {account_id} - {count:,} transactions")

    # Ask user which account to analyze (loop until valid input)
    selected_account_id = None

    while selected_account_id is None:
        print(f"\n{'='*70}")
        user_input = input("\nEntrez le nom du partenaire OU l'account_id à analyser (ou 'q' pour quitter): ").strip()

        # Allow user to quit
        if user_input.lower() == 'q':
            print("\nAu revoir!")
            exit(0)

        # First, check if it's a direct account ID match
        if user_input in transactions_df['partner_id'].values:
            selected_account_id = user_input
        # Otherwise, try to find by name
        elif account_mapping is not None:
            # Search by name (case insensitive, partial match)
            matching = account_mapping[
                account_mapping['partner_name'].str.lower().str.contains(user_input.lower(), na=False)
            ]

            if len(matching) == 0:
                print(f"\nERREUR: Aucun partenaire trouvé avec '{user_input}'")
                print("Veuillez réessayer.")
            elif len(matching) == 1:
                selected_account_id = matching.iloc[0]['account_id']
                partner_name = matching.iloc[0]['partner_name']
                print(f"\nPartenaire trouvé: {partner_name} (Account ID: {selected_account_id})")
            else:
                # Multiple matches - group by partner_name to show unique partners
                unique_partners = matching[['partner_name', 'account_id']].drop_duplicates('partner_name')
                print(f"\nPlusieurs partenaires trouvés ({len(unique_partners)}):")
                for idx, row in unique_partners.head(10).iterrows():
                    print(f"  - {row['partner_name']} (Account ID: {row['account_id']})")
                print("\nVeuillez entrer le nom exact OU l'Account ID du partenaire souhaité.")
        else:
            print(f"\nERREUR: Account ID '{user_input}' non trouvé!")
            print("Veuillez réessayer.")

    # Run analysis if account found
    if selected_account_id and selected_account_id in transactions_df['partner_id'].values:
        # Get partner name if available
        found_partner_name = None
        if account_mapping is not None:
            partner_info = account_mapping[account_mapping['account_id'] == selected_account_id]
            if not partner_info.empty and pd.notna(partner_info.iloc[0].get('partner_name')):
                found_partner_name = partner_info.iloc[0]['partner_name']

        analysis_result = run_all_features(
            transactions_df,
            accounts_df,
            partner_id=selected_account_id,
            partner_name=found_partner_name,
            save_json=True
        )

        print(f"\n{'='*70}")
        print(f"ANALYSIS COMPLETE")
        print(f"{'='*70}")
        print(f"\n📊 Summary:")
        print(f"  HIGH risk features: {analysis_result['summary']['high_risk_features']}")
        print(f"  MEDIUM risk features: {analysis_result['summary']['medium_risk_features']}")
        print(f"  LOW risk features: {analysis_result['summary']['low_risk_features']}")
        print(f"  Average risk score: {analysis_result['summary']['average_risk_score']}/100")
        print()
    elif selected_account_id:
        print(f"\nERREUR: Account ID '{selected_account_id}' n'a pas de transactions!")
        print("Veuillez réessayer avec un account_id valide.")
