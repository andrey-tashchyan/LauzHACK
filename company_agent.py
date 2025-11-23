"""
Company information agent powered by Together.ai (GPT-OSS-120B).

It fuses what we have:
- partner.csv / partner_country.csv: identity, address, country, industry, dates
- client_risk_summary.csv: anomaly score
- top_100_suspects_20251123_101101.csv: top suspicious partners
- partner_role.csv + business_rel.csv + br_to_account.csv + account.csv: business
  relationships and accounts for the company
- (optional) Pappers registry JSON if present in data_lauzhack_2/pappers_companies.json

Setup:
  pip install -r requirements.txt
  export TOGETHER_API_KEY= key

Usage:
  python company_agent.py "Where is Blum & Co located and are there any associated workers?"
"""

from __future__ import annotations

import argparse
import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

try:
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_together import ChatTogether
except Exception:  # pragma: no cover - allow offline usage
    ChatTogether = None
    ChatPromptTemplate = None


ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data_lauzhack_2"
SUSPECTS_CSV = DATA_DIR / "top_100_suspects_20251123_101101.csv"
COMPANY_JSON = DATA_DIR / "swiss_companies_dataset.json"


def _normalize(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()


def load_companies() -> List[Dict[str, Any]]:
    with COMPANY_JSON.open(encoding="utf-8") as f:
        return json.load(f)


def load_worker_lookup() -> Dict[str, List[Dict[str, Any]]]:
    """Build a map of company_id -> list of associated individuals (workers/relations)."""
    partner = pd.read_csv(DATA_DIR / "partner.csv")
    role = pd.read_csv(DATA_DIR / "partner_role.csv")

    def _parse_birth_year(value: Any) -> int | None:
        if pd.isna(value):
            return None
        text = str(value)
        # Accept pure years or full dates like 1981-04-07
        match = re.search(r"(18|19|20)\\d{2}", text)
        return int(match.group()) if match else None

    # Rows where associated_partner_id points to an entity (often a company)
    assoc = role[role["associated_partner_id"].notna()].copy()
    assoc = assoc.merge(
        partner[["partner_id", "partner_name", "partner_gender", "partner_birth_year"]],
        on="partner_id",
        how="left",
    )

    lookup: Dict[str, List[Dict[str, Any]]] = {}
    for _, row in assoc.iterrows():
        company_id = row["associated_partner_id"]
        worker = {
            "partner_id": row["partner_id"],
            "name": row["partner_name"],
            "gender": row["partner_gender"],
            "birth_year": _parse_birth_year(row["partner_birth_year"]),
            "relationship_start_date": row["relationship_start_date"],
            "relationship_end_date": row["relationship_end_date"],
            "relationship_type": row["br_type_code"],
        }
        lookup.setdefault(company_id, []).append(worker)
    return lookup


def load_registry() -> Dict[str, Dict[str, Any]]:
    """
    Load Pappers registry data if available.
    Expect a JSON list with partner_id or a map keyed by partner_id.
    """
    candidates = [
        DATA_DIR / "pappers_companies.json",
        DATA_DIR / "pappers_registry.json",
    ]
    for path in candidates:
        if path.exists():
            try:
                with path.open(encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    return data
                if isinstance(data, list):
                    reg = {}
                    for item in data:
                        pid = item.get("partner_id") or item.get("id")
                        if pid:
                            reg[str(pid)] = item
                    return reg
            except Exception:
                pass
    return {}


def load_suspects(partner_class: Optional[str] = None) -> pd.DataFrame:
    """
    Load the top suspects list and optionally filter by partner class code.
    """
    suspects = pd.read_csv(SUSPECTS_CSV).copy()
    suspects.insert(0, "watch_rank", range(1, len(suspects) + 1))
    suspects["watch_reason"] = suspects.apply(
        lambda row: (
            f"Overall risk {row.get('overall_risk_level')} (score {row.get('aggregate_risk_score')}); "
            f"high={row.get('high_risk_features')}, medium={row.get('medium_risk_features')}, "
            f"low={row.get('low_risk_features')}; total_transactions={row.get('total_transactions')}"
        ),
        axis=1,
    )
    if partner_class:
        partner = pd.read_csv(DATA_DIR / "partner.csv")[["partner_id", "partner_class_code"]]
        suspects = (
            suspects.merge(partner, on="partner_id", how="left")
            .query("partner_class_code == @partner_class")
            .drop(columns=["partner_class_code"])
        )
    return suspects


class CompanyQAAgent:
    def __init__(self, model: str = "openai/gpt-oss-120b", temperature: float = 0.0):
        self.partner_df = pd.read_csv(DATA_DIR / "partner.csv")
        self.partner_country_df = pd.read_csv(DATA_DIR / "partner_country.csv")
        self.risk_df = pd.read_csv(DATA_DIR / "client_risk_summary.csv")
        suspects_raw = load_suspects()
        suspects_with_class = suspects_raw.merge(
            self.partner_df[["partner_id", "partner_class_code"]],
            on="partner_id",
            how="left",
        )
        # Company-only watchlist for company questions
        self.watchlist_df = (
            suspects_with_class[suspects_with_class["partner_class_code"] == "B"]
            .drop(columns=["partner_class_code"])
        )
        self.company_watchlist_map = {
            str(row["partner_id"]): row.to_dict()
            for _, row in self.watchlist_df.iterrows()
            if pd.notna(row.get("partner_id"))
        }
        # People-only watchlist to flag worker hits
        people_watchlist_df = suspects_with_class[suspects_with_class["partner_class_code"] == "I"].drop(columns=["partner_class_code"])
        self.people_watchlist_map = {
            str(row["partner_id"]): row.to_dict()
            for _, row in people_watchlist_df.iterrows()
            if pd.notna(row.get("partner_id"))
        }
        self.partner_role_df = pd.read_csv(DATA_DIR / "partner_role.csv")
        self.business_rel_df = pd.read_csv(DATA_DIR / "business_rel.csv")
        self.br_to_account_df = pd.read_csv(DATA_DIR / "br_to_account.csv")
        self.account_df = pd.read_csv(DATA_DIR / "account.csv")
        self.companies = load_companies()
        self.worker_lookup = load_worker_lookup()
        self.registry = load_registry()

        self.llm_available = ChatTogether is not None and ChatPromptTemplate is not None
        self.llm = ChatTogether(model=model, temperature=temperature) if self.llm_available else None
        self.prompt = (
            ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        (
                        "You are an AML assistant answering questions about companies. "
                        "Use the supplied structured data. "
                        "If data is missing (e.g., registry/Pappers), say so briefly. "
                        "Be concise; for simple info requests return a short summary (name, address, risk/anomaly). "
                        "Always list associated individuals (workers/relations) when present and flag any worker watchlist hits."
                    ),
                ),
                    (
                        "human",
                        (
                            "Question: {question}\n\n"
                            "Candidate companies (top fuzzy matches):\n{company_context}\n\n"
                            "Associated individuals (workers/relations):\n{worker_context}"
                        ),
                    ),
                ]
            )
            if self.llm_available
            else None
        )

    def _best_matches(self, question: str, top_k: int = 3) -> List[Dict[str, Any]]:
        scored = []
        q_norm = _normalize(question)
        for company in self.companies:
            name = company.get("nom_entreprise") or company.get("denomination") or ""
            if not isinstance(name, str):
                name = ""
            n_norm = _normalize(name)
            if n_norm and n_norm in q_norm:
                score = 1.0
            else:
                score = _similarity(q_norm, n_norm)
            scored.append((score, company))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for s, c in scored if s >= 0.2][:top_k]

    def _business_relationships(self, partner_id: str) -> List[Dict[str, Any]]:
        rows = self.partner_role_df[
            (self.partner_role_df["partner_id"] == partner_id)
            & (self.partner_role_df["entity_type"] == "BR")
        ]
        rels = []
        for _, r in rows.iterrows():
            br_id = r["entity_id"]
            br_row = self.business_rel_df[self.business_rel_df["br_id"] == br_id]
            br_info = br_row.iloc[0].to_dict() if not br_row.empty else {}

            accounts = []
            links = self.br_to_account_df[self.br_to_account_df["br_id"] == br_id]
            if not links.empty:
                joined = links.merge(self.account_df, on="account_id", how="left")
                for _, a in joined.iterrows():
                    accounts.append(
                        {
                            "account_id": a.get("account_id"),
                            "account_iban": a.get("account_iban"),
                            "account_currency": a.get("account_currency"),
                            "account_open_date": a.get("account_open_date"),
                            "account_close_date": a.get("account_close_date"),
                        }
                    )

            rels.append(
                {
                    "br_id": br_id,
                    "br_open_date": br_info.get("br_open_date"),
                    "br_close_date": br_info.get("br_close_date"),
                    "relationship_start_date": r.get("relationship_start_date"),
                    "relationship_end_date": r.get("relationship_end_date"),
                    "br_type_code": r.get("br_type_code"),
                    "accounts": accounts,
                }
            )
        return rels

    def _company_context(self, question: str) -> List[Dict[str, Any]]:
        matches = self._best_matches(question)
        enriched = []
        for c in matches:
            pid = c.get("partner_id")
            registry = self.registry.get(pid)

            country_row = self.partner_country_df[self.partner_country_df["partner_id"] == pid]
            country_info = country_row.iloc[0].to_dict() if not country_row.empty else {}

            risk_row = self.risk_df[self.risk_df["partner_id"] == pid]
            risk_info = risk_row.iloc[0].to_dict() if not risk_row.empty else {}

            watch_info = self.company_watchlist_map.get(str(pid), {})

            rels = self._business_relationships(pid)

            enriched.append(
                {
                    "partner_id": pid,
                    "nom_entreprise": c.get("nom_entreprise"),
                    "denomination": c.get("denomination"),
                    "industry_gic2_code": c.get("industrie_gic2_code"),
                    "partner_address": c.get("siege") or c.get("partner_address"),
                    "partner_open_date": c.get("date_creation") or c.get("partner_open_date"),
                    "partner_close_date": c.get("date_cessation") or c.get("partner_close_date"),
                    "telephone": c.get("telephone"),
                    "country": country_info.get("country_name"),
                    "suspect_country": country_info.get("suspect_country"),
                    "anomaly_score": risk_info.get("anomaly_score"),
                    "is_anomalous": risk_info.get("is_anomalous"),
                    "watchlist": watch_info if watch_info else None,
                    "registry": registry,
                    "business_relationships": rels,
                }
            )
        return enriched

    def _worker_context(self, matches: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        result: Dict[str, List[Dict[str, Any]]] = {}
        for c in matches:
            company_id = c.get("partner_id")
            if not company_id:
                continue
            workers = self.worker_lookup.get(company_id, [])
            if workers:
                enriched_workers: List[Dict[str, Any]] = []
                for worker in workers:
                    w = dict(worker)
                    watch_hit = self.people_watchlist_map.get(str(w.get("partner_id")))
                    if watch_hit:
                        w["watchlist"] = {
                            "watch_rank": watch_hit.get("watch_rank"),
                            "reason": watch_hit.get("watch_reason"),
                            "risk_level": watch_hit.get("overall_risk_level"),
                            "risk_score": watch_hit.get("aggregate_risk_score"),
                        }
                    enriched_workers.append(w)
                result[company_id] = enriched_workers
        return result

    def answer(self, question: str) -> str:
        companies = self._company_context(question)
        workers = self._worker_context(companies)

        # Basic deterministic answer for simple queries (address / anomaly) when a single company matches
        q_norm = _normalize(question)
        if len(companies) == 1 and any(k in q_norm for k in ["address", "located", "anomaly", "status", "basic", "info"]):
            c = companies[0]
            company_id = c.get("partner_id")
            addr = c.get("partner_address") or {}
            if isinstance(addr, dict):
                addr_str = ", ".join(str(v) for v in addr.values() if v)
            else:
                addr_str = str(addr) if addr else "unknown address"
            anomaly = c.get("is_anomalous")
            anomaly_score = c.get("anomaly_score")
            anomaly_str = "unknown"
            if anomaly is True:
                anomaly_str = "anomalous"
            elif anomaly is False:
                anomaly_str = "not anomalous"
            worker_entries = []
            watch_warnings = []
            company_workers = workers.get(company_id, []) if company_id else []
            if company_workers:
                for w in company_workers:
                    details = []
                    if w.get("relationship_type"):
                        details.append(str(w["relationship_type"]))
                    start = w.get("relationship_start_date")
                    end = w.get("relationship_end_date")
                    if start or end:
                        details.append(f"from {start or '?'} to {end or 'present'}")
                    if w.get("birth_year"):
                        details.append(f"b.{w['birth_year']}")
                    label = w.get("name") or "Unknown worker"
                    if details:
                        label += f" ({'; '.join(details)})"
                    worker_entries.append(label)
                    if w.get("watchlist"):
                        reason = w["watchlist"].get("reason") or "on suspects list"
                        watch_warnings.append(f"{w.get('name') or 'Unknown worker'} flagged: {reason}")
            worker_str = "; ".join(worker_entries) if worker_entries else "none on file"
            return (
                f"{c.get('nom_entreprise') or c.get('denomination')}: "
                f"address: {addr_str}; anomaly status: {anomaly_str}"
                + (f" (score {anomaly_score})" if anomaly_score is not None else "")
                + f"; workers: {worker_str}"
                + (f" WARNING: {'; '.join(watch_warnings)}" if watch_warnings else "")
            )

        if not self.llm_available:
            return json.dumps(
                {
                    "companies": companies,
                    "workers": workers,
                    "note": "Install langchain-core, langchain-community, langchain-together and set TOGETHER_API_KEY for LLM answers.",
                },
                ensure_ascii=False,
                indent=2,
            )

        messages = self.prompt.format_messages(
            question=question,
            company_context=json.dumps(companies, ensure_ascii=False, indent=2),
            worker_context=json.dumps(workers, ensure_ascii=False, indent=2),
        )
        response = self.llm.invoke(messages)
        return response.content


def main() -> None:
    parser = argparse.ArgumentParser(description="QA agent for Swiss companies.")
    parser.add_argument("question", help="Question to ask about a company.")
    parser.add_argument(
        "--model",
        default="openai/gpt-oss-120b",
        help="Together model name (default: openai/gpt-oss-120b).",
    )
    args = parser.parse_args()

    agent = CompanyQAAgent(model=args.model)
    print(agent.answer(args.question))


if __name__ == "__main__":
    main()
