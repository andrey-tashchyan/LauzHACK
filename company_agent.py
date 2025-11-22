"""
Lightweight LangChain agent for Q&A on Swiss companies.

Setup:
  pip install langchain-core langchain-community langchain-together together pandas
  export TOGETHER_API_KEY= key

Usage:
  python company_agent.py "What is the address of Blum & Co.?"
"""

from __future__ import annotations

import argparse
import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from langchain_core.prompts import ChatPromptTemplate
from langchain_together import ChatTogether


ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data_lauzhack_2"
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


class CompanyQAAgent:
    def __init__(self, model: str = "openai/gpt-oss-120b", temperature: float = 0.0):
        self.companies = load_companies()
        self.worker_lookup = load_worker_lookup()
        self.llm = ChatTogether(model=model, temperature=temperature)
        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    (
                        "You answer questions about Swiss companies using the provided JSON data. "
                        "Prefer precise fields over speculation. "
                        "If information is missing, say so briefly. "
                        "Treat 'workers' as individuals linked in the partner_role CSV when available."
                    ),
                ),
                (
                    "human",
                    (
                        "Question: {question}\n\n"
                        "Candidate companies (top fuzzy matches):\n{company_context}\n\n"
                        "Associated individuals (from partner_role/partner.csv):\n{worker_context}"
                    ),
                ),
            ]
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

    def _company_context(self, question: str) -> List[Dict[str, Any]]:
        matches = self._best_matches(question)
        slimmed = []
        for c in matches:
            slimmed.append(
                {
                    "partner_id": c.get("partner_id"),
                    "nom_entreprise": c.get("nom_entreprise"),
                    "industry": c.get("industrie_gic2_code"),
                    "address": c.get("siege"),
                    "telephone": c.get("telephone"),
                    "anomaly_score": c.get("anomaly_score"),
                    "is_anomalous": c.get("is_anomalous"),
                    "statut_rcs": c.get("statut_rcs"),
                    "date_creation": c.get("date_creation"),
                    "date_cessation": c.get("date_cessation"),
                }
            )
        return slimmed

    def _worker_context(self, matches: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        result: Dict[str, List[Dict[str, Any]]] = {}
        for c in matches:
            company_id = c.get("partner_id")
            if not company_id:
                continue
            workers = self.worker_lookup.get(company_id, [])
            if workers:
                result[company_id] = workers
        return result

    def answer(self, question: str) -> str:
        companies = self._company_context(question)
        workers = self._worker_context(companies)

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
