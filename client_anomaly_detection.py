"""
Analyse comportementale et détection d'anomalies clients.

Placez ce script dans le même répertoire que le fichier CSV
(`joined_with_transactions.csv` ou `joined_with_transcation.csv`) puis lancez-le.
Il produit :
  - client_risk_summary.csv : synthèse par client + score d'anomalie
  - anomalous_transactions.csv : transactions détaillées pour les clients atypiques

Modifiez les variables `START_DATE` et `END_DATE` ci-dessous pour restreindre la période.
"""

from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


# --------------------------------------------------------------------------- #
# User parameters                                                             #
# --------------------------------------------------------------------------- #
# Define the date window to analyse. Use None to leave unbounded on that side.
START_DATE = None  # e.g. "2023-01-01"
END_DATE = None  # e.g. "2023-12-31"

# IsolationForest contamination (expected proportion of anomalies)
CONTAMINATION = 0.05

# Input CSV candidates (the script picks the first that exists)
INPUT_CSV_CANDIDATES = [
    Path("joined_with_transactions.csv"),
    Path("joined_with_transcation.csv"),  # typo-friendly fallback
    Path("data_lauzhack_2/joined_with_transactions.csv"),
    Path("data_lauzhack_2/joined_with_transcation.csv"),
]


def find_input_file(candidates: List[Path]) -> Path:
    """Return the first existing path among the candidates."""
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError(
        "Aucun fichier CSV trouvé. Placez 'joined_with_transactions.csv' "
        "à côté de ce script ou mettez à jour INPUT_CSV_CANDIDATES."
    )


def resolve_columns(df: pd.DataFrame) -> Dict[str, str]:
    """
    Map expected logical fields to actual column names in the CSV.
    Raises if a required column is missing and prints available columns to guide fixes.
    """
    candidate_map = {
        "partner_id": ["partner_id", "client_id", "customer_id"],
        "partner_name": ["partner_name", "client_name", "customer_name", "full_name"],
        "date": ["Date", "date", "transaction_date"],
        "debit_credit": ["Debit/Credit", "debit_credit", "direction"],
        "amount": ["Amount", "amount", "transaction_amount"],
        "tx_id": ["Transaction ID", "transaction_id", "tx_id"],
        "currency": ["account_currency", "Currency", "currency"],
        "ext_counterparty_country": [
            "ext_counterparty_country",
            "counterparty_country",
            "ext_country",
        ],
        "ext_counterparty_account_id": [
            "ext_counterparty_Account_ID",
            "ext_counterparty_account_id",
            "counterparty_account_id",
        ],
        "transfer_type": ["Transfer_Type", "transfer_type"],
        "balance": ["Balance", "balance"],
        "account_id": ["account_id", "Account ID"],
    }

    resolved: Dict[str, str] = {}
    for logical_name, candidates in candidate_map.items():
        for col in candidates:
            if col in df.columns:
                resolved[logical_name] = col
                break

    required = ["partner_id", "date", "debit_credit", "amount", "tx_id", "currency"]
    missing_required = [name for name in required if name not in resolved]
    if missing_required:
        print("Colonnes disponibles :", list(df.columns))
        raise KeyError(
            f"Colonnes obligatoires manquantes : {missing_required}. "
            "Mettez à jour 'candidate_map' dans resolve_columns pour refléter vos noms de colonnes."
        )

    # Fill optional columns with placeholders if absent so downstream code stays simple.
    optional_with_defaults = {
        "partner_name": "Unknown",
        "ext_counterparty_country": pd.NA,
        "ext_counterparty_account_id": pd.NA,
        "transfer_type": pd.NA,
        "balance": pd.NA,
        "account_id": pd.NA,
    }
    for optional_col, default_val in optional_with_defaults.items():
        if optional_col not in resolved:
            # Create a synthetic column to keep the pipeline intact.
            synthetic_name = f"__{optional_col}_placeholder__"
            df[synthetic_name] = default_val
            resolved[optional_col] = synthetic_name
            print(f"Info: colonne '{optional_col}' absente, création d'un placeholder.")

    return resolved


def load_transactions(file_path: Path) -> pd.DataFrame:
    """Load CSV and standardise key columns."""
    df = pd.read_csv(file_path)
    column_map = resolve_columns(df)

    # Ensure standard working columns exist while preserving the original dataset.
    for std_name, original in column_map.items():
        if std_name not in df.columns:
            df[std_name] = df[original]
        elif std_name != original:
            df[std_name] = df[original]

    # Parse dates.
    df["tx_date"] = pd.to_datetime(df[column_map["date"]], errors="coerce")
    df = df.dropna(subset=["tx_date"]).copy()

    # Clean numeric amount.
    df["amount_value"] = pd.to_numeric(df[column_map["amount"]], errors="coerce").fillna(0.0)
    # Debit/Credit flag normalized to lowercase for filtering.
    df["debit_credit_flag"] = (
        df[column_map["debit_credit"]].astype(str).str.lower().str.strip()
    )
    df["is_credit"] = df["debit_credit_flag"] == "credit"
    df["is_debit"] = df["debit_credit_flag"] == "debit"
    df["amount_in"] = np.where(df["is_credit"], df["amount_value"], 0.0)
    df["amount_out"] = np.where(df["is_debit"], df["amount_value"], 0.0)
    df["amount_abs"] = df["amount_value"].abs()

    # Country and currency cleaning for categorical features.
    df["currency_clean"] = (
        df[column_map["currency"]].fillna("UNKNOWN").astype(str).str.strip()
    )
    country_series = df[column_map["ext_counterparty_country"]]
    df["is_cross_border"] = country_series.notna() & country_series.astype(str).str.strip().ne("")

    # Partner name placeholder.
    df["partner_name"] = df[column_map["partner_name"]].fillna("Unknown").astype(str)

    # Standard transaction identifier.
    df["tx_id_std"] = df[column_map["tx_id"]]

    return df


def filter_by_date(df: pd.DataFrame, start_date: Optional[str], end_date: Optional[str]) -> pd.DataFrame:
    """Filter transactions to the user-defined date window."""
    mask = pd.Series(True, index=df.index)
    if start_date:
        mask &= df["tx_date"] >= pd.to_datetime(start_date)
    if end_date:
        mask &= df["tx_date"] <= pd.to_datetime(end_date)
    filtered = df.loc[mask].copy()
    print(
        f"Période filtrée : {start_date or '-inf'} -> {end_date or '+inf'} | "
        f"{len(filtered):,} transactions conservées."
    )
    return filtered


def build_client_features(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate behavioural features per client."""
    grouped = df.groupby("partner_id")

    features = grouped.agg(
        partner_name=("partner_name", "first"),
        n_tx=("tx_id_std", "count"),
        total_in=("amount_in", "sum"),
        total_out=("amount_out", "sum"),
        avg_amount=("amount_abs", "mean"),
        max_amount=("amount_abs", "max"),
        n_cross_border=("is_cross_border", "sum"),
        n_currencies=("currency_clean", pd.Series.nunique),
    ).reset_index()

    features["net_flow"] = features["total_in"] - features["total_out"]
    features["share_cross_border"] = np.where(
        features["n_tx"] > 0, features["n_cross_border"] / features["n_tx"], 0.0
    )

    # Replace any residual NaNs from empty groups.
    numeric_cols = [
        "n_tx",
        "total_in",
        "total_out",
        "net_flow",
        "avg_amount",
        "max_amount",
        "n_cross_border",
        "share_cross_border",
        "n_currencies",
    ]
    features[numeric_cols] = features[numeric_cols].fillna(0.0)

    return features


def detect_anomalies(features: pd.DataFrame) -> pd.DataFrame:
    """
    Fit IsolationForest on behavioural features and score anomalies.
    Higher `anomaly_score` => more atypical.
    """
    numeric_cols = [
        "n_tx",
        "total_in",
        "total_out",
        "net_flow",
        "avg_amount",
        "max_amount",
        "n_cross_border",
        "share_cross_border",
        "n_currencies",
    ]

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(features[numeric_cols])

    model = IsolationForest(
        random_state=42,
        contamination=CONTAMINATION,
        n_estimators=300,
        n_jobs=-1,
    )
    model.fit(X_scaled)

    raw_score = model.decision_function(X_scaled)
    features = features.copy()
    features["anomaly_score"] = -raw_score  # invert so higher = more anomalous
    features["is_anomalous"] = model.predict(X_scaled) == -1

    # Order from most suspicious to least.
    features = features.sort_values(by="anomaly_score", ascending=False).reset_index(drop=True)
    return features


def build_anomalous_transactions(df: pd.DataFrame, anomalous_ids: pd.Series) -> pd.DataFrame:
    """Extract detailed transactions for anomalous clients."""
    subset = df[df["partner_id"].isin(set(anomalous_ids))].copy()
    if subset.empty:
        return subset

    subset["Date"] = subset["tx_date"]
    subset["Transaction ID"] = subset["tx_id_std"]
    subset["Debit/Credit"] = subset["debit_credit_flag"]
    subset["Amount"] = subset["amount_value"]
    subset["Currency"] = subset["currency_clean"]

    desired_cols = [
        "partner_id",
        "partner_name",
        "Date",
        "Transaction ID",
        "Debit/Credit",
        "Amount",
        "Currency",
        "ext_counterparty_country",
        "ext_counterparty_Account_ID",
        "ext_counterparty_account_id",
        "Transfer_Type",
        "transfer_type",
        "Balance",
        "balance",
        "account_id",
        "Account ID",
    ]
    available_cols = [col for col in desired_cols if col in subset.columns]

    # Keep the first occurrence of each logical column to avoid duplicates.
    unique_ordered_cols = list(dict.fromkeys(available_cols))
    subset = subset[unique_ordered_cols].sort_values(["partner_id", "Date"])
    return subset


def main() -> None:
    input_path = find_input_file(INPUT_CSV_CANDIDATES)
    print(f"Lecture du fichier : {input_path}")

    df_raw = load_transactions(input_path)
    df_period = filter_by_date(df_raw, START_DATE, END_DATE)

    client_features = build_client_features(df_period)
    client_risk_summary = detect_anomalies(client_features)

    # Save client risk summary.
    summary_path = input_path.parent / "client_risk_summary.csv"
    client_risk_summary.to_csv(summary_path, index=False)
    print(f"Synthèse client enregistrée : {summary_path}")

    # Extract and save transactions for anomalous clients only.
    anomalous_ids = client_risk_summary.loc[
        client_risk_summary["is_anomalous"], "partner_id"
    ]
    anomalous_transactions = build_anomalous_transactions(df_period, anomalous_ids)
    anomalous_path = input_path.parent / "anomalous_transactions.csv"
    anomalous_transactions.to_csv(anomalous_path, index=False)
    print(f"Transactions atypiques enregistrées : {anomalous_path} ({len(anomalous_transactions):,} lignes)")

    # Display top 20 most anomalous clients.
    top_clients = client_risk_summary.head(20)
    print("\nTop clients atypiques :")
    for _, row in top_clients.iterrows():
        print(
            f"- Client {row['partner_id']}: n_tx={row['n_tx']}, "
            f"total_in={row['total_in']:.2f}, total_out={row['total_out']:.2f}, "
            f"share_cross_border={row['share_cross_border']:.2%}, "
            f"anomaly_score={row['anomaly_score']:.4f}, anomalous={row['is_anomalous']}"
        )


if __name__ == "__main__":
    main()
