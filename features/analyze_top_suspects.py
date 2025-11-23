"""
AML Analysis - Identify Top 100 Most Suspicious Partners

This script analyzes ALL partners in the joined_transactions_fixed dataset
and ranks them by suspicion level using all AML features.

Usage:
    python3 -m features.analyze_top_suspects
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime
from io import StringIO

# Import all feature functions
from .feature_frequency import feature_frequency
from .feature_burst_structuring import feature_burst_structuring
from .feature_atypical_amounts import feature_atypical_amounts
from .feature_cross_border import feature_cross_border
from .feature_counterparties import feature_counterparties
from .feature_irregularity import feature_irregularity
from .feature_night_activity import feature_night_activity
from .feature_ephemeral_account import feature_ephemeral_account


def load_dataset():
    """Load the joined_transactions_fixed dataset."""
    possible_paths = [
        'features/joined_transactioned_fixed.csv',
        'features/joined_transactions_fixed.csv',
        'data_lauzhack_2/joined_transactioned_fixed.csv',
        'data_lauzhack_2/joined_transactions_fixed.csv',
        'joined_transactioned_fixed.csv',
        'joined_transactions_fixed.csv',
        # Parquet versions
        'features/joined_transactioned_fixed.parquet',
        'features/joined_transactions_fixed.parquet',
        'data_lauzhack_2/joined_transactioned_fixed.parquet',
        'data_lauzhack_2/joined_transactions_fixed.parquet',
    ]

    for path in possible_paths:
        if os.path.exists(path):
            print(f"Loading dataset from: {path}")
            if path.endswith('.parquet'):
                return pd.read_parquet(path)
            else:
                return pd.read_csv(path)

    raise FileNotFoundError(
        "Could not find joined_transactions_fixed dataset. "
        "Please ensure it exists in features/ or data_lauzhack_2/ directory."
    )


def analyze_partner(partner_id, transactions_df):
    """
    Analyze a single partner using all AML features.

    Returns dict with risk scores or None if analysis fails.
    """
    try:
        # Suppress output
        old_stdout = sys.stdout
        sys.stdout = StringIO()

        # Run all features
        results = {}

        # 1. Frequency
        try:
            result = feature_frequency(transactions_df, partner_id=partner_id, return_data=True)
            if result:
                results['frequency'] = result
        except Exception as e:
            pass

        # 2. Burst/Structuring
        try:
            result = feature_burst_structuring(transactions_df, partner_id=partner_id, return_data=True)
            if result:
                results['burst_structuring'] = result
        except Exception as e:
            pass

        # 3. Atypical Amounts
        try:
            result = feature_atypical_amounts(transactions_df, partner_id=partner_id, return_data=True)
            if result:
                results['atypical_amounts'] = result
        except Exception as e:
            pass

        # 4. Cross Border
        try:
            result = feature_cross_border(transactions_df, partner_id=partner_id, return_data=True)
            if result:
                results['cross_border'] = result
        except Exception as e:
            pass

        # 5. Counterparties
        try:
            result = feature_counterparties(transactions_df, partner_id=partner_id, return_data=True)
            if result:
                results['counterparties'] = result
        except Exception as e:
            pass

        # 6. Irregularity
        try:
            result = feature_irregularity(transactions_df, partner_id=partner_id, return_data=True)
            if result:
                results['irregularity'] = result
        except Exception as e:
            pass

        # 7. Night Activity
        try:
            result = feature_night_activity(transactions_df, partner_id=partner_id, return_data=True)
            if result:
                results['night_activity'] = result
        except Exception as e:
            pass

        # 8. Ephemeral Account
        try:
            result = feature_ephemeral_account(transactions_df, partner_id=partner_id, return_data=True)
            if result:
                results['ephemeral_account'] = result
        except Exception as e:
            pass

        # Restore stdout
        sys.stdout = old_stdout

        return results if results else None

    except Exception as e:
        sys.stdout = old_stdout
        return None


def calculate_aggregate_score(feature_results):
    """
    Calculate aggregate risk score from all feature results.

    Returns: (aggregate_score, overall_risk_level, risk_counts, feature_scores)
    """
    risk_scores = []
    feature_scores = {}
    risk_levels = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}

    for feature_name, feature_data in feature_results.items():
        if feature_data and isinstance(feature_data, dict):
            score = feature_data.get('risk_score', 0)
            level = feature_data.get('risk_level', 'LOW')

            if score is not None:
                risk_scores.append(score)
                feature_scores[feature_name] = {
                    'score': score,
                    'level': level,
                    'reasons': feature_data.get('risk_reasons', [])
                }

            if level in risk_levels:
                risk_levels[level] += 1

    # Calculate weighted aggregate score
    if risk_scores:
        avg_risk_score = sum(risk_scores) / len(risk_scores)
        # Bonus for having multiple HIGH risk features
        high_risk_bonus = risk_levels["HIGH"] * 5
        aggregate_score = min(100, avg_risk_score + high_risk_bonus)
    else:
        aggregate_score = 0

    # Determine overall risk level
    if aggregate_score >= 70 or risk_levels["HIGH"] >= 3:
        overall_risk = "HIGH"
    elif aggregate_score >= 40 or risk_levels["HIGH"] >= 1:
        overall_risk = "MEDIUM"
    else:
        overall_risk = "LOW"

    return aggregate_score, overall_risk, risk_levels, feature_scores


def get_partner_name(partner_id, transactions_df):
    """Extract partner name from transactions."""
    name = None

    if 'partner_name_incoming' in transactions_df.columns:
        name_matches = transactions_df[
            transactions_df['partner_id_incoming'] == partner_id
        ]['partner_name_incoming'].dropna()
        if len(name_matches) > 0:
            name = name_matches.iloc[0]

    if not name and 'partner_name_outgoing' in transactions_df.columns:
        name_matches = transactions_df[
            transactions_df['partner_id_outgoing'] == partner_id
        ]['partner_name_outgoing'].dropna()
        if len(name_matches) > 0:
            name = name_matches.iloc[0]

    return name if name else "N/A"


def analyze_all_partners(min_transactions=5, top_n=100):
    """
    Main function: Analyze all partners and return top suspects.

    Parameters:
    -----------
    min_transactions : int
        Minimum number of transactions to analyze a partner
    top_n : int
        Number of top suspects to return

    Returns:
    --------
    pd.DataFrame : Top N most suspicious partners with detailed stats
    """
    print("\n" + "="*80)
    print("ANALYSE COMPLÈTE - DÉTECTION DES PARTENAIRES SUSPECTS")
    print("="*80)

    # Step 1: Load dataset
    print("\n[1/5] Chargement du dataset...")
    try:
        transactions_df = load_dataset()
        print(f"      ✓ {len(transactions_df):,} transactions chargées")
    except Exception as e:
        print(f"      ✗ ERREUR: {e}")
        return pd.DataFrame()

    # Step 2: Identify all partners
    print("\n[2/5] Identification des partenaires...")
    partner_incoming = transactions_df['partner_id_incoming'].value_counts()
    partner_outgoing = transactions_df['partner_id_outgoing'].value_counts()
    all_partners = pd.concat([partner_incoming, partner_outgoing]).groupby(level=0).sum().sort_values(ascending=False)

    partners_to_analyze = all_partners[all_partners >= min_transactions]
    print(f"      ✓ {len(all_partners):,} partenaires uniques")
    print(f"      ✓ {len(partners_to_analyze):,} partenaires avec ≥{min_transactions} transactions (à analyser)")

    # Step 3: Analyze each partner
    print(f"\n[3/5] Analyse de {len(partners_to_analyze):,} partenaires...")
    print("      " + "-"*70)

    results = []
    total_partners = len(partners_to_analyze)

    for idx, (partner_id, tx_count) in enumerate(partners_to_analyze.items(), 1):
        # Progress indicator
        if idx % 100 == 0:
            print(f"      Progression: {idx:,}/{total_partners:,} ({100*idx/total_partners:.1f}%)")
        elif idx == 1 or idx % 10 == 0:
            print(f"      Progression: {idx:,}/{total_partners:,} ({100*idx/total_partners:.1f}%)", end='\r')

        # Analyze partner
        feature_results = analyze_partner(partner_id, transactions_df)

        if not feature_results:
            continue

        # Calculate aggregate score
        aggregate_score, overall_risk, risk_counts, feature_scores = calculate_aggregate_score(feature_results)

        # Get partner name
        partner_name = get_partner_name(partner_id, transactions_df)

        # Store result
        results.append({
            'partner_id': partner_id,
            'partner_name': partner_name,
            'total_transactions': int(tx_count),
            'aggregate_risk_score': round(aggregate_score, 2),
            'overall_risk_level': overall_risk,
            'high_risk_features': risk_counts["HIGH"],
            'medium_risk_features': risk_counts["MEDIUM"],
            'low_risk_features': risk_counts["LOW"],
            'feature_details': feature_scores
        })

    print()  # New line after progress
    print(f"      ✓ Analyse terminée: {len(results):,} partenaires analysés")

    # Step 4: Sort and get top suspects
    print("\n[4/5] Classement par niveau de risque...")
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('aggregate_risk_score', ascending=False)

    top_suspects = results_df.head(top_n)

    # Display summary statistics
    print(f"      ✓ HIGH risk:   {len(results_df[results_df['overall_risk_level'] == 'HIGH']):,} partenaires")
    print(f"      ✓ MEDIUM risk: {len(results_df[results_df['overall_risk_level'] == 'MEDIUM']):,} partenaires")
    print(f"      ✓ LOW risk:    {len(results_df[results_df['overall_risk_level'] == 'LOW']):,} partenaires")

    # Step 5: Save results
    print(f"\n[5/5] Sauvegarde des résultats...")
    output_dir = "analysis_results"
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save CSV (simple version)
    csv_filename = os.path.join(output_dir, f"top_{top_n}_suspects_{timestamp}.csv")
    top_suspects_simple = top_suspects[[
        'partner_id', 'partner_name', 'total_transactions',
        'aggregate_risk_score', 'overall_risk_level',
        'high_risk_features', 'medium_risk_features', 'low_risk_features'
    ]]
    top_suspects_simple.to_csv(csv_filename, index=False, encoding='utf-8')
    print(f"      ✓ CSV sauvegardé: {csv_filename}")

    # Save JSON (detailed version with all feature scores)
    json_filename = os.path.join(output_dir, f"top_{top_n}_suspects_detailed_{timestamp}.json")
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(top_suspects.to_dict(orient='records'), f, indent=2, ensure_ascii=False, default=str)
    print(f"      ✓ JSON détaillé sauvegardé: {json_filename}")

    # Display top 20 suspects
    print("\n" + "="*80)
    print(f"TOP {min(20, len(top_suspects))} PARTENAIRES LES PLUS SUSPECTS:")
    print("="*80)
    print(f"{'#':<4} {'Nom':<36} {'Score':<7} {'Risque':<7} {'TX':<6} {'H M L':<7}")
    print("-"*80)

    for idx, row in top_suspects.head(20).iterrows():
        name_truncated = row['partner_name'][:35] if len(row['partner_name']) > 35 else row['partner_name']
        print(f"{idx+1:<4} {name_truncated:<36} "
              f"{row['aggregate_risk_score']:>6.1f} "
              f"{row['overall_risk_level']:<7} "
              f"{row['total_transactions']:>5} "
              f"{row['high_risk_features']:>1} {row['medium_risk_features']:>1} {row['low_risk_features']:>1}")

    if len(top_suspects) > 20:
        print(f"\n... et {len(top_suspects) - 20} autres partenaires suspects")

    print("\n" + "="*80)
    print("ANALYSE TERMINÉE")
    print("="*80)
    print(f"\nFichiers sauvegardés dans: {output_dir}/")
    print(f"  - {os.path.basename(csv_filename)}")
    print(f"  - {os.path.basename(json_filename)}")
    print()

    return top_suspects


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Analyze all partners and identify top 100 most suspicious",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze all partners and get top 100 suspects
  python3 -m features.analyze_top_suspects

  # Get top 50 suspects with minimum 10 transactions
  python3 -m features.analyze_top_suspects --top 50 --min-tx 10

  # Get top 200 suspects
  python3 -m features.analyze_top_suspects --top 200
        """
    )

    parser.add_argument(
        '--top',
        type=int,
        default=100,
        help='Number of top suspects to return (default: 100)'
    )

    parser.add_argument(
        '--min-tx',
        type=int,
        default=5,
        help='Minimum number of transactions to analyze a partner (default: 5)'
    )

    args = parser.parse_args()

    # Run the analysis
    results = analyze_all_partners(
        min_transactions=args.min_tx,
        top_n=args.top
    )
