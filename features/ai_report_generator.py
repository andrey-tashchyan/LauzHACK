"""
AI Report Generator - Example of how an AI can generate natural language reports from AML analysis JSON

This script shows how to load the JSON output from run_all_features and generate human-readable narratives.
"""

import json
import sys
from datetime import datetime


def generate_narrative_report(json_file):
    """
    Generate a natural language report from AML analysis JSON.

    Parameters:
    -----------
    json_file : str
        Path to the analysis JSON file

    Returns:
    --------
    str
        Natural language report
    """
    # Load the JSON
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Extract metadata
    metadata = data['analysis_metadata']
    summary = data['summary']
    features = data['features']

    partner_name = metadata.get('partner_name', 'Unknown')
    partner_id = metadata['partner_id']
    timestamp = datetime.fromisoformat(metadata['analysis_timestamp']).strftime("%Y-%m-%d %H:%M:%S")

    # Start building the report
    report = []
    report.append("="*80)
    report.append("ANTI-MONEY LAUNDERING ANALYSIS REPORT")
    report.append("="*80)
    report.append("")
    report.append(f"Client: {partner_name} (ID: {partner_id})")
    report.append(f"Analysis Date: {timestamp}")
    report.append("")
    report.append("-"*80)
    report.append("EXECUTIVE SUMMARY")
    report.append("-"*80)
    report.append("")

    # Overall risk assessment
    avg_risk = summary['average_risk_score']
    if avg_risk >= 70:
        overall_risk = "HIGH"
        risk_description = "This client presents significant AML risk indicators and requires immediate review."
    elif avg_risk >= 40:
        overall_risk = "MEDIUM"
        risk_description = "This client shows moderate AML risk indicators. Enhanced monitoring recommended."
    else:
        overall_risk = "LOW"
        risk_description = "This client shows minimal AML risk indicators based on current analysis."

    report.append(f"Overall Risk Level: {overall_risk}")
    report.append(f"Risk Score: {avg_risk}/100")
    report.append("")
    report.append(risk_description)
    report.append("")
    report.append(f"Features Analyzed: {metadata['total_features_analyzed']}")
    report.append(f"  - HIGH risk: {summary['high_risk_features']} features")
    report.append(f"  - MEDIUM risk: {summary['medium_risk_features']} features")
    report.append(f"  - LOW risk: {summary['low_risk_features']} features")
    report.append("")

    # Detailed findings
    report.append("-"*80)
    report.append("DETAILED FINDINGS")
    report.append("-"*80)
    report.append("")

    # Sort features by risk score (highest first)
    sorted_features = sorted(features, key=lambda x: x.get('risk_score', 0), reverse=True)

    for idx, feature in enumerate(sorted_features, 1):
        feature_name = feature['feature_name'].replace('_', ' ').title()
        risk_level = feature.get('risk_level', 'UNKNOWN')
        risk_score = feature.get('risk_score', 0)

        report.append(f"{idx}. {feature_name}")
        report.append(f"   Risk Level: {risk_level} (Score: {risk_score}/100)")
        report.append("")

        # Generate narrative based on feature type
        if feature['feature_name'] == 'frequency':
            metrics = feature['metrics']
            report.append(f"   The client executed {metrics['total_transactions']:,} transactions")
            report.append(f"   over a {metrics['date_range_days']} day period ({metrics['start_date']} to {metrics['end_date']}).")
            report.append(f"   This represents an average of {metrics['tx_per_day_avg']} transactions per day,")
            report.append(f"   with a peak of {metrics['max_daily']} transactions on a single day.")
            report.append("")

            # Risk reasons
            if feature.get('risk_reasons'):
                report.append("   Key Observations:")
                for reason in feature['risk_reasons']:
                    report.append(f"   - {reason}")
                report.append("")

        elif feature['feature_name'] == 'burst_structuring':
            metrics = feature['metrics']
            report.append(f"   Detected {metrics.get('burst_hours', 0)} hours with concentrated transaction activity")
            report.append(f"   (more than {metrics.get('burst_threshold', 5)} transactions within one hour).")
            report.append(f"   Identified {metrics.get('potential_structuring', 0)} transactions with amounts")
            report.append(f"   just below common reporting thresholds, which may indicate structuring.")
            report.append("")

            if feature.get('risk_reasons'):
                report.append("   Key Observations:")
                for reason in feature['risk_reasons']:
                    report.append(f"   - {reason}")
                report.append("")

        elif feature['feature_name'] == 'atypical_amounts':
            metrics = feature['metrics']
            report.append(f"   Out of {metrics.get('total_transactions', 0)} transactions,")
            report.append(f"   {metrics.get('outlier_count', 0)} ({metrics.get('outlier_pct', 0):.1f}%) were identified as outliers")
            report.append(f"   using statistical analysis (IQR method).")
            report.append(f"   Median transaction amount: {metrics.get('median_amount', 0):,.2f}")
            report.append(f"   Maximum transaction amount: {metrics.get('max_amount', 0):,.2f}")
            report.append("")

            if feature.get('risk_reasons'):
                report.append("   Key Observations:")
                for reason in feature['risk_reasons']:
                    report.append(f"   - {reason}")
                report.append("")

        elif feature['feature_name'] == 'cross_border':
            metrics = feature['metrics']
            total = metrics.get('total_transactions', 0)
            cross_border = metrics.get('cross_border_count', 0)
            high_risk = metrics.get('high_risk_count', 0)

            report.append(f"   {cross_border:,} out of {total:,} transactions ({metrics.get('cross_border_pct', 0):.1f}%)")
            report.append(f"   involved international counterparties across {metrics.get('unique_countries', 0)} different countries.")

            if high_risk > 0:
                report.append(f"   CRITICAL: {high_risk} transactions involved high-risk jurisdictions.")
                report.append(f"   High-risk countries identified: {', '.join(metrics.get('high_risk_countries_found', []))}")
            report.append("")

            if feature.get('risk_reasons'):
                report.append("   Key Observations:")
                for reason in feature['risk_reasons']:
                    report.append(f"   - {reason}")
                report.append("")

        # Generic handling for other features
        else:
            if feature.get('risk_reasons'):
                report.append("   Key Observations:")
                for reason in feature['risk_reasons']:
                    report.append(f"   - {reason}")
                report.append("")

    # Recommendations
    report.append("-"*80)
    report.append("RECOMMENDATIONS")
    report.append("-"*80)
    report.append("")

    if avg_risk >= 70:
        report.append("IMMEDIATE ACTIONS REQUIRED:")
        report.append("1. Escalate this case to senior compliance officer for review")
        report.append("2. Conduct enhanced due diligence on the client")
        report.append("3. Review recent transaction activity for suspicious patterns")
        report.append("4. Consider filing a Suspicious Activity Report (SAR) if warranted")
        report.append("5. Implement enhanced monitoring on all accounts")
    elif avg_risk >= 40:
        report.append("RECOMMENDED ACTIONS:")
        report.append("1. Place client on enhanced monitoring list")
        report.append("2. Review high-risk feature findings in detail")
        report.append("3. Request additional documentation for unusual transactions")
        report.append("4. Schedule periodic reviews (monthly)")
    else:
        report.append("STANDARD MONITORING:")
        report.append("1. Continue standard monitoring procedures")
        report.append("2. Conduct annual review as per policy")
        report.append("3. No immediate action required")

    report.append("")
    report.append("="*80)
    report.append(f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("="*80)

    return "\n".join(report)


def generate_short_summary(json_file):
    """
    Generate a short one-paragraph summary suitable for dashboards or alerts.

    Parameters:
    -----------
    json_file : str
        Path to the analysis JSON file

    Returns:
    --------
    str
        Short summary paragraph
    """
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    metadata = data['analysis_metadata']
    summary = data['summary']

    partner_name = metadata.get('partner_name', 'Unknown client')
    avg_risk = summary['average_risk_score']
    high_count = summary['high_risk_features']

    if avg_risk >= 70:
        return (f"⚠️ HIGH RISK ALERT: {partner_name} shows significant AML risk indicators "
                f"with an overall risk score of {avg_risk}/100. {high_count} features flagged as HIGH risk. "
                f"Immediate review recommended.")
    elif avg_risk >= 40:
        return (f"⚡ MEDIUM RISK: {partner_name} exhibits moderate AML risk patterns "
                f"(risk score: {avg_risk}/100). {high_count} HIGH risk features detected. "
                f"Enhanced monitoring advised.")
    else:
        return (f"✓ LOW RISK: {partner_name} shows minimal AML risk indicators "
                f"(risk score: {avg_risk}/100). Standard monitoring procedures apply.")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python ai_report_generator.py <analysis_json_file>")
        print("\nExample:")
        print("  python ai_report_generator.py analysis_2f07ef4f_20251122_183045.json")
        sys.exit(1)

    json_file = sys.argv[1]

    try:
        # Generate full report
        print(generate_narrative_report(json_file))
        print("\n" + "="*80 + "\n")

        # Generate short summary
        print("SHORT SUMMARY:")
        print(generate_short_summary(json_file))

    except FileNotFoundError:
        print(f"Error: File '{json_file}' not found")
    except json.JSONDecodeError:
        print(f"Error: '{json_file}' is not a valid JSON file")
    except Exception as e:
        print(f"Error: {e}")
