from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data_lauzhack_2"


def parse_address(raw: str) -> tuple[str | None, str | None, str | None]:
    """Split the stored address into street, postal code, and city."""
    if not isinstance(raw, str):
        return None, None, None

    line1, line2 = (raw.split("\n", 1) + [""])[:2]
    postal = city = None
    if line2:
        match = re.match(r"^(?P<postal>\d{4,5})\s+(?P<city>.+)$", line2.strip())
        if match:
            postal = match.group("postal")
            city = match.group("city")

    line1 = line1.strip() or None
    return line1, postal, city


def build_dataset() -> list[dict]:
    partner = pd.read_csv(DATA_DIR / "partner.csv")
    country = pd.read_csv(DATA_DIR / "partner_country.csv")
    risk = pd.read_csv(DATA_DIR / "client_risk_summary.csv")

    swiss_ids = set(country[country["country_name"] == "Switzerland"]["partner_id"])
    companies = partner[
        (partner["industry_gic2_code"] != "Individual")
        & partner["partner_id"].isin(swiss_ids)
    ].copy()

    companies = companies.merge(
        country[["partner_id", "suspect_country", "country_name"]],
        on="partner_id",
        how="left",
    )
    companies = companies.merge(
        risk[["partner_id", "anomaly_score", "is_anomalous"]],
        on="partner_id",
        how="left",
    )

    records: list[dict] = []
    for _, row in companies.iterrows():
        street, postal, city = parse_address(row["partner_address"])
        record = {
            "partner_id": row["partner_id"],
            "nom_entreprise": row["partner_name"],
            "denomination": row["partner_name"],
            "personne_morale": True,
            "partner_class_code": row["partner_class_code"],
            "statut_rcs": "inscrit" if pd.isna(row["partner_close_date"]) else "radie",
            "entreprise_cessee": bool(pd.notna(row["partner_close_date"])),
            "date_creation": row["partner_open_date"],
            "date_cessation": row["partner_close_date"]
            if pd.notna(row["partner_close_date"])
            else None,
            "industrie_gic2_code": row["industry_gic2_code"],
            "telephone": row["partner_phone_number"]
            if pd.notna(row["partner_phone_number"])
            else None,
            "siege": {
                "adresse_ligne_1": street,
                "code_postal": postal,
                "ville": city,
                "pays": row["country_name"]
                if isinstance(row["country_name"], str)
                else "Switzerland",
            },
            "suspect_country": bool(row["suspect_country"])
            if not pd.isna(row["suspect_country"])
            else False,
            "anomaly_score": float(row["anomaly_score"])
            if pd.notna(row["anomaly_score"])
            else None,
            "is_anomalous": bool(row["is_anomalous"])
            if not pd.isna(row["is_anomalous"])
            else None,
            "source": "partner.csv / partner_country.csv / client_risk_summary.csv",
        }
        records.append(record)

    return records


def main() -> None:
    records = build_dataset()
    out_path = DATA_DIR / "swiss_companies_dataset.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(records)} companies to {out_path}")


if __name__ == "__main__":
    main()
