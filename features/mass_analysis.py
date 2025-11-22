"""
AML Mass Analysis - Red and Yellow Lists Generator

This script analyzes ALL clients and generates:
- Red List: HIGH risk clients
- Yellow List: MEDIUM risk clients
"""

import pandas as pd
import json
from datetime import datetime
from aml_utils import load_data
from functions.feature_frequency import feature_frequency
from functions.feature_burst_structuring import feature_burst_structuring
from functions.feature_atypical_amounts import feature_atypical_amounts
from functions.feature_cross_border import feature_cross_border
from functions.feature_counterparties import feature_counterparties
from functions.feature_irregularity import feature_irregularity
from functions.feature_night_activity import feature_night_activity
from functions.feature_ephemeral_account import feature_ephemeral_account
from functions.feature_abnormal_activity import feature_abnormal_activity


def analyze_single_client(partner_id, partner_name, transactions_df, accounts_df):
    """
    Analyze a single client and return risk assessment.

    Returns:
    --------
    dict: {
        'partner_id': str,
        'partner_name': str,
        'total_transactions': int,
        'high_risk_features': int,
        'medium_risk_features': int,
        'low_risk_features': int,
        'average_risk_score': float,
        'overall_risk_level': str (HIGH/MEDIUM/LOW),
        'feature_details': list of feature results
    }
    """
    results = []

    # Run all transaction-based features
    features_to_run = [
        feature_frequency,
        feature_burst_structuring,
        feature_atypical_amounts,
        feature_cross_border,
        feature_counterparties,
        feature_irregularity,
        feature_night_activity
    ]

    for feature_func in features_to_run:
        try:
            result = feature_func(transactions_df, partner_id)
            if result:
                result['partner_name'] = partner_name
                results.append(result)
        except Exception as e:
            print(f"  ⚠️  Error in {feature_func.__name__}: {e}")

    # Account-based features
    try:
        result = feature_ephemeral_account(transactions_df, accounts_df, partner_id)
        if result:
            result['partner_name'] = partner_name
            results.append(result)
    except Exception as e:
        print(f"  ⚠️  Error in feature_ephemeral_account: {e}")

    try:
        result = feature_abnormal_activity(transactions_df, accounts_df, partner_id)
        if result:
            result['partner_name'] = partner_name
            results.append(result)
    except Exception as e:
        print(f"  ⚠️  Error in feature_abnormal_activity: {e}")

    # Calculate statistics
    high_risk_count = len([r for r in results if r.get('risk_level') == 'HIGH'])
    medium_risk_count = len([r for r in results if r.get('risk_level') == 'MEDIUM'])
    low_risk_count = len([r for r in results if r.get('risk_level') == 'LOW'])

    avg_risk_score = round(sum([r.get('risk_score', 0) for r in results]) / len(results), 2) if results else 0

    # Determine overall risk level
    # RED LIST: >= 2 HIGH risk features OR average score >= 70
    # YELLOW LIST: >= 1 HIGH risk feature OR >= 3 MEDIUM risk features OR average score >= 50
    if high_risk_count >= 2 or avg_risk_score >= 70:
        overall_risk = "HIGH"
    elif high_risk_count >= 1 or medium_risk_count >= 3 or avg_risk_score >= 50:
        overall_risk = "MEDIUM"
    else:
        overall_risk = "LOW"

    # Get transaction count
    client_transactions = transactions_df[transactions_df['partner_id'] == partner_id]
    total_tx = len(client_transactions)

    return {
        'partner_id': partner_id,
        'partner_name': partner_name,
        'total_transactions': total_tx,
        'high_risk_features': high_risk_count,
        'medium_risk_features': medium_risk_count,
        'low_risk_features': low_risk_count,
        'average_risk_score': avg_risk_score,
        'overall_risk_level': overall_risk,
        'feature_details': results
    }


def run_mass_analysis(transactions_df, accounts_df, account_mapping=None, min_transactions=5):
    """
    Analyze all clients and generate red/yellow lists.

    Parameters:
    -----------
    transactions_df : pd.DataFrame
        Transaction data
    accounts_df : pd.DataFrame
        Account data
    account_mapping : pd.DataFrame, optional
        Mapping of account_id to partner_name
    min_transactions : int
        Minimum number of transactions to analyze a client (default: 5)

    Returns:
    --------
    dict: {
        'red_list': list of HIGH risk clients,
        'yellow_list': list of MEDIUM risk clients,
        'green_list': list of LOW risk clients,
        'statistics': summary stats
    }
    """
    print(f"\n{'='*70}")
    print(f"MASS AML ANALYSIS - ANALYZING ALL CLIENTS")
    print(f"{'='*70}\n")

    # Get all unique partner IDs with transaction counts
    partner_counts = transactions_df['partner_id'].value_counts()

    # Filter by minimum transactions
    partners_to_analyze = partner_counts[partner_counts >= min_transactions].index.tolist()

    print(f"📊 Found {len(partner_counts)} unique clients")
    print(f"📊 Analyzing {len(partners_to_analyze)} clients with >= {min_transactions} transactions\n")

    red_list = []
    yellow_list = []
    green_list = []

    # Analyze each partner
    for idx, partner_id in enumerate(partners_to_analyze, 1):
        # Get partner name if available
        partner_name = None
        if account_mapping is not None:
            partner_info = account_mapping[account_mapping['account_id'] == partner_id]
            if not partner_info.empty and pd.notna(partner_info.iloc[0].get('partner_name')):
                partner_name = partner_info.iloc[0]['partner_name']

        display_name = partner_name if partner_name else partner_id
        print(f"[{idx}/{len(partners_to_analyze)}] Analyzing: {display_name}...")

        # Analyze client
        analysis = analyze_single_client(partner_id, partner_name, transactions_df, accounts_df)

        # Add to appropriate list
        if analysis['overall_risk_level'] == 'HIGH':
            red_list.append(analysis)
            print(f"  🔴 RED LIST - Score: {analysis['average_risk_score']}/100, HIGH features: {analysis['high_risk_features']}")
        elif analysis['overall_risk_level'] == 'MEDIUM':
            yellow_list.append(analysis)
            print(f"  🟡 YELLOW LIST - Score: {analysis['average_risk_score']}/100, HIGH features: {analysis['high_risk_features']}")
        else:
            green_list.append(analysis)
            print(f"  🟢 GREEN LIST - Score: {analysis['average_risk_score']}/100")

    # Sort lists by risk score (descending)
    red_list.sort(key=lambda x: x['average_risk_score'], reverse=True)
    yellow_list.sort(key=lambda x: x['average_risk_score'], reverse=True)
    green_list.sort(key=lambda x: x['average_risk_score'], reverse=True)

    # Create summary statistics
    statistics = {
        'total_clients_analyzed': len(partners_to_analyze),
        'red_list_count': len(red_list),
        'yellow_list_count': len(yellow_list),
        'green_list_count': len(green_list),
        'red_list_percentage': round(len(red_list) / len(partners_to_analyze) * 100, 2) if partners_to_analyze else 0,
        'yellow_list_percentage': round(len(yellow_list) / len(partners_to_analyze) * 100, 2) if partners_to_analyze else 0,
        'analysis_timestamp': datetime.now().isoformat(),
        'min_transactions_threshold': min_transactions
    }

    return {
        'red_list': red_list,
        'yellow_list': yellow_list,
        'green_list': green_list,
        'statistics': statistics
    }


def save_results(results, output_dir='json_files'):
    """Save analysis results to JSON files."""
    import os

    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save full results
    full_results_file = f"{output_dir}/mass_analysis_full_{timestamp}.json"
    with open(full_results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Full results saved to: {full_results_file}")

    # Save red list summary (simplified)
    red_list_summary = [{
        'partner_id': client['partner_id'],
        'partner_name': client['partner_name'],
        'total_transactions': client['total_transactions'],
        'average_risk_score': client['average_risk_score'],
        'high_risk_features': client['high_risk_features'],
        'medium_risk_features': client['medium_risk_features']
    } for client in results['red_list']]

    red_list_file = f"{output_dir}/red_list_{timestamp}.json"
    with open(red_list_file, 'w', encoding='utf-8') as f:
        json.dump(red_list_summary, f, indent=2, ensure_ascii=False)
    print(f"🔴 Red list saved to: {red_list_file}")

    # Save yellow list summary (simplified)
    yellow_list_summary = [{
        'partner_id': client['partner_id'],
        'partner_name': client['partner_name'],
        'total_transactions': client['total_transactions'],
        'average_risk_score': client['average_risk_score'],
        'high_risk_features': client['high_risk_features'],
        'medium_risk_features': client['medium_risk_features']
    } for client in results['yellow_list']]

    yellow_list_file = f"{output_dir}/yellow_list_{timestamp}.json"
    with open(yellow_list_file, 'w', encoding='utf-8') as f:
        json.dump(yellow_list_summary, f, indent=2, ensure_ascii=False)
    print(f"🟡 Yellow list saved to: {yellow_list_file}")

    return full_results_file, red_list_file, yellow_list_file


def print_summary(results):
    """Print a summary of the analysis results."""
    stats = results['statistics']

    print(f"\n{'='*70}")
    print(f"MASS ANALYSIS SUMMARY")
    print(f"{'='*70}\n")

    print(f"📊 Total clients analyzed: {stats['total_clients_analyzed']}")
    print(f"   (Minimum {stats['min_transactions_threshold']} transactions per client)\n")

    print(f"🔴 RED LIST (HIGH RISK): {stats['red_list_count']} clients ({stats['red_list_percentage']}%)")
    if results['red_list']:
        print(f"   Top 5 highest risk:")
        for idx, client in enumerate(results['red_list'][:5], 1):
            name = client['partner_name'] if client['partner_name'] else client['partner_id']
            print(f"   {idx}. {name} - Score: {client['average_risk_score']}/100, HIGH features: {client['high_risk_features']}")

    print(f"\n🟡 YELLOW LIST (MEDIUM RISK): {stats['yellow_list_count']} clients ({stats['yellow_list_percentage']}%)")
    if results['yellow_list']:
        print(f"   Top 5 highest risk:")
        for idx, client in enumerate(results['yellow_list'][:5], 1):
            name = client['partner_name'] if client['partner_name'] else client['partner_id']
            print(f"   {idx}. {name} - Score: {client['average_risk_score']}/100, HIGH features: {client['high_risk_features']}")

    print(f"\n🟢 GREEN LIST (LOW RISK): {stats['green_list_count']} clients")
    print()


if __name__ == '__main__':
    print("="*70)
    print("AML MASS ANALYSIS - RED & YELLOW LISTS GENERATOR")
    print("="*70)

    # Load data
    print("\n📂 Loading data...")
    transactions_df, accounts_df = load_data()
    print(f"✓ Loaded {len(transactions_df):,} transactions")
    print(f"✓ Loaded {len(accounts_df):,} accounts")

    # Load partner data for names
    account_mapping = None
    try:
        partners_df = pd.read_csv('LauzHACK/partner.csv')
        partner_role_df = pd.read_csv('LauzHACK/partner_role.csv')
        br_to_account_df = pd.read_csv('LauzHACK/br_to_account.csv')

        partner_br = partner_role_df[partner_role_df['entity_type'] == 'BR'][['partner_id', 'entity_id']]
        partner_br.columns = ['partner_id', 'br_id']

        account_mapping = br_to_account_df.merge(partner_br, on='br_id', how='left')
        account_mapping = account_mapping.merge(partners_df[['partner_id', 'partner_name']], on='partner_id', how='left')

        print(f"✓ Loaded {len(partners_df):,} partners with name mapping")
    except Exception as e:
        print(f"⚠️  Could not load partner mapping ({e}), using IDs only")

    # Ask for minimum transaction threshold
    print(f"\n{'='*70}")
    min_tx_input = input("\nMinimum number of transactions per client to analyze (default: 5): ").strip()
    min_transactions = int(min_tx_input) if min_tx_input else 5

    # Run mass analysis
    results = run_mass_analysis(transactions_df, accounts_df, account_mapping, min_transactions)

    # Print summary
    print_summary(results)

    # Save results
    save_results(results)

    print(f"\n{'='*70}")
    print(f"✓ ANALYSIS COMPLETE")
    print(f"{'='*70}\n")
