"""
Account information agent powered by Together.ai (GPT-OSS-120B).

Given a free-form question, the agent:
- Resolves a partner by name or ID (or via account ID).
- Surfaces core KYC attributes (gender, name, birth year, onboarding note, address).
- Checks the top suspects list and suspicious industry list.
- Summarises country of residence and outbound payment countries.
- Runs AML feature analytics (features/run_all_features.py) and lets the LLM pick
  the most relevant metrics for the question.
- For very basic “give info about X” style questions, responds with a fixed structure:
  • Industry + whether it is suspicious
  • Country of residence + countries where money is sent
  • Business relationship

Usage:
    export TOGETHER_API_KEY=...
    python account_agent.py "Give info about Claus Brunner"
"""

from __future__ import annotations

import argparse
import ast
import io
import json
import re
from contextlib import redirect_stdout
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

try:
    from together import Together  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    Together = None


class _MockChatMessage:
    def __init__(self, content: str):
        self.content = content


class _MockChoice:
    def __init__(self, content: str):
        self.message = _MockChatMessage(content)


class _MockResponse:
    def __init__(self, content: str):
        self.choices = [_MockChoice(content)]


class _MockChat:
    def __init__(self):
        self.completions = self

    def create(self, *args, **kwargs):
        return _MockResponse("[mock llm output] Install 'together' and set TOGETHER_API_KEY for real answers.")


class _MockClient:
    def __init__(self):
        self.chat = _MockChat()

from sent_amounts_by_country import amount_sent_per_country, load_transactions as load_tx_for_countries
from features.run_all_features import run_all_features

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data_lauzhack_2"
SUSPECTS_CSV = DATA_DIR / "top_100_suspects_20251123_101101.csv"

# Fallback suspicious industry list (kept in sync with add_suspicious_industries.py)
FALLBACK_SUSPICIOUS_INDUSTRIES = [
    "Investment intermediation",
    "O. financial intermediation n.e.c.",
    "Regulated broker",
    "Other non-life insurance n.e.c.",
    "Act. head offices of o. companies",
    "Management of real estate",
    "Letting of own or leased land",
    "Buying & selling of own real estate",
    "Real estate activities",
    "Accounting, bookkeeping activities",
    "Attorney, notary practice",
    "Creative, arts & entertainment act.",
    "Ma. & assembly of watches & clocks",
    "Food & beverage service activities",
    "Hotels, inns & guesthouses w. rest.",
    "Cult., educ., scient.& research org.",
]


def _normalize(text: str) -> str:
    if not isinstance(text, str):
        return ""
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def load_suspicious_industries() -> List[str]:
    """
    Read suspicious_industries from add_suspicious_industries.py without executing it.
    Falls back to the hardcoded list if parsing fails.
    """
    path = ROOT / "add_suspicious_industries.py"
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "suspicious_industries":
                        return ast.literal_eval(node.value)
    except Exception:
        pass
    return FALLBACK_SUSPICIOUS_INDUSTRIES


def _parse_dates(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def load_partner_core() -> pd.DataFrame:
    partner_df = pd.read_csv(DATA_DIR / "partner.csv")
    return _parse_dates(partner_df, ["partner_birth_year", "partner_open_date", "partner_close_date"])


def load_partner_country() -> pd.DataFrame:
    partner_country = pd.read_csv(DATA_DIR / "partner_country.csv")
    return partner_country


def load_onboarding_notes() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "client_onboarding_notes.csv")


def load_watchlist(partner_class: Optional[str] = None) -> pd.DataFrame:
    """
    Load the top suspects list and optionally filter by partner_class_code.
    Used to keep people/company watchlists separated.
    """
    watch = pd.read_csv(SUSPECTS_CSV).copy()
    watch.insert(0, "watch_rank", range(1, len(watch) + 1))
    watch["watch_reason"] = watch.apply(
        lambda row: (
            f"Overall risk {row.get('overall_risk_level')} (score {row.get('aggregate_risk_score')}); "
            f"high={row.get('high_risk_features')}, medium={row.get('medium_risk_features')}, "
            f"low={row.get('low_risk_features')}; total_transactions={row.get('total_transactions')}"
        ),
        axis=1,
    )
    if partner_class:
        partner = pd.read_csv(DATA_DIR / "partner.csv")[["partner_id", "partner_class_code"]]
        watch = (
            watch.merge(partner, on="partner_id", how="left")
            .query("partner_class_code == @partner_class")
            .drop(columns=["partner_class_code"])
        )
    return watch


def load_relationships() -> Tuple[pd.DataFrame, pd.DataFrame]:
    partner_role = pd.read_csv(DATA_DIR / "partner_role.csv")
    business_rel = pd.read_csv(DATA_DIR / "business_rel.csv")
    return partner_role, business_rel


def load_account_mapping() -> Tuple[pd.DataFrame, pd.DataFrame]:
    br_to_account = pd.read_csv(DATA_DIR / "br_to_account.csv")
    account_df = pd.read_csv(DATA_DIR / "account.csv")
    return br_to_account, _parse_dates(account_df, ["account_open_date", "account_close_date"])


def load_feature_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Prepare DataFrames for feature computation (run_all_features).
    Uses joined_with_transactions.csv for partner_id context.
    """
    tx_candidates = [
        ROOT / "joined_with_transactions.csv",
        ROOT / "joined_with_transcation.csv",
        DATA_DIR / "joined_with_transactions.csv",
        DATA_DIR / "joined_with_transcation.csv",
        DATA_DIR / "transactions.csv",
    ]

    tx_path: Optional[Path] = None
    for path in tx_candidates:
        if path.exists():
            tx_path = path
            break
    if tx_path is None:
        raise FileNotFoundError("No joined_with_transactions.csv found for feature analysis.")

    tx_df = pd.read_csv(tx_path)
    # Normalize column names
    rename_map = {
        "counterparty_Account_ID": "counterparty_account_id",
        "ext_counterparty_Account_ID": "ext_counterparty_account_id",
        "ext_counterparty_country": "ext_counterparty_country",
        "Account ID": "account_id",
    }
    tx_df = tx_df.rename(columns=rename_map)

    if "Date" in tx_df.columns:
        tx_df["Date"] = pd.to_datetime(tx_df["Date"], errors="coerce")
        tx_df = tx_df.dropna(subset=["Date"]).copy()
    if "Amount" in tx_df.columns:
        tx_df["Amount"] = pd.to_numeric(tx_df["Amount"], errors="coerce").fillna(0.0)
    # Attach partner_id if missing by mapping account_id -> partner_id via BR mapping
    if "partner_id" not in tx_df.columns:
        try:
            partner_role_df = pd.read_csv(DATA_DIR / "partner_role.csv")
            br_to_account_df = pd.read_csv(DATA_DIR / "br_to_account.csv")
            partner_br = partner_role_df[partner_role_df["entity_type"] == "BR"][["partner_id", "entity_id"]]
            partner_br.columns = ["partner_id", "br_id"]
            mapping = br_to_account_df.merge(partner_br, on="br_id", how="left")
            acct_to_partner = {str(r.account_id): str(r.partner_id) for r in mapping.itertuples() if pd.notna(r.account_id) and pd.notna(r.partner_id)}
            if "account_id" not in tx_df.columns and "Account ID" in tx_df.columns:
                tx_df["account_id"] = tx_df["Account ID"]
            tx_df["partner_id"] = tx_df["account_id"].astype(str).map(acct_to_partner)
        except Exception:
            pass

    # Provide placeholder incoming/outgoing columns expected by newer feature functions
    # If we don't have bilateral info, fall back to partner_id and ext country.
    country_map = {}
    try:
        partner_country_df = pd.read_csv(DATA_DIR / "partner_country.csv")
        domicile = partner_country_df[partner_country_df["country_type"].str.lower() == "domicile"]
        country_map = {str(r.partner_id): r.country_name for r in domicile.itertuples() if pd.notna(r.partner_id)}
        status_map = {str(r.partner_id): r.partner_country_status_code for r in domicile.itertuples() if pd.notna(r.partner_id)}
    except Exception:
        country_map = {}
        status_map = {}

    def _ensure_col(name: str, value):
        if name not in tx_df.columns:
            if isinstance(value, pd.DataFrame):
                tx_df[name] = value.iloc[:, 0]
            else:
                tx_df[name] = value

    _ensure_col("partner_id_outgoing", tx_df.get("partner_id"))
    _ensure_col("partner_id_incoming", tx_df.get("partner_id"))
    _ensure_col("country_name_outgoing", tx_df["partner_id"].map(country_map) if "partner_id" in tx_df.columns else None)
    _ensure_col("country_name_incoming", tx_df["partner_id"].map(country_map) if "partner_id" in tx_df.columns else None)
    _ensure_col("partner_country_status_code_outgoing", tx_df["partner_id"].map(status_map) if "partner_id" in tx_df.columns else None)
    _ensure_col("partner_country_status_code_incoming", tx_df["partner_id"].map(status_map) if "partner_id" in tx_df.columns else None)
    _ensure_col("industry_gic2_code_outgoing", tx_df.get("industry_gic2_code"))
    _ensure_col("industry_gic2_code_incoming", tx_df.get("industry_gic2_code"))
    _ensure_col("account_id_outgoing", tx_df.get("account_id"))
    _ensure_col("account_id_incoming", tx_df.get("account_id"))
    # Clean Debit/Credit casing
    if "Debit/Credit" in tx_df.columns:
        tx_df["Debit/Credit"] = tx_df["Debit/Credit"].astype(str).str.lower()

    account_df = pd.read_csv(DATA_DIR / "account.csv")
    account_df = _parse_dates(account_df, ["account_open_date", "account_close_date"])
    # Map account metadata into transaction frame for feature functions expecting *_outgoing fields
    if "account_id" in tx_df.columns:
        open_map = {str(r.account_id): r.account_open_date for r in account_df.itertuples() if pd.notna(r.account_id)}
        close_map = {str(r.account_id): r.account_close_date for r in account_df.itertuples() if pd.notna(r.account_id)}
        currency_map = {str(r.account_id): r.account_currency for r in account_df.itertuples() if pd.notna(r.account_id)}
        acct_series = tx_df["account_id"]
        if isinstance(acct_series, pd.DataFrame):
            acct_series = acct_series.iloc[:, 0]
        acct_series = acct_series.astype(str)
        tx_df["account_open_date"] = acct_series.map(open_map)
        tx_df["account_close_date"] = acct_series.map(close_map)
        tx_df["account_currency"] = acct_series.map(currency_map)
        _ensure_col("account_open_date_outgoing", tx_df["account_open_date"])
        _ensure_col("account_open_date_incoming", tx_df["account_open_date"])
        _ensure_col("account_close_date_outgoing", tx_df["account_close_date"])
        _ensure_col("account_close_date_incoming", tx_df["account_close_date"])
        _ensure_col("account_currency_outgoing", tx_df["account_currency"])
        _ensure_col("account_currency_incoming", tx_df["account_currency"])
    return tx_df, account_df


def find_tx_file_for_countries() -> Path:
    candidates = [
        ROOT / "transactions.csv",
        DATA_DIR / "transactions.csv",
        ROOT / "joined_with_transactions.csv",
        DATA_DIR / "joined_with_transactions.csv",
    ]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError("No transaction CSV found for outgoing country analysis.")


def pick_country_of_residence(partner_country_df: pd.DataFrame, partner_id: str) -> Optional[str]:
    subset = partner_country_df[partner_country_df["partner_id"] == partner_id]
    if subset.empty:
        return None
    domicile = subset[subset["country_type"].str.lower() == "domicile"]
    if not domicile.empty:
        return domicile.iloc[0]["country_name"]
    return subset.iloc[0]["country_name"]


def country_breakdown(partner_country_df: pd.DataFrame, partner_id: str) -> Dict[str, List[str]]:
    """
    Return countries by type (domicile, tax, mailing) for a partner.
    Only keeps active rows (status code 1) when available.
    """
    subset = partner_country_df[partner_country_df["partner_id"] == partner_id]
    if subset.empty:
        return {}
    active = subset[subset["partner_country_status_code"] == 1]
    if not active.empty:
        subset = active
    breakdown: Dict[str, List[str]] = {}
    for _, row in subset.iterrows():
        ctype = str(row.get("country_type")).lower()
        cname = row.get("country_name")
        if pd.isna(cname):
            continue
        breakdown.setdefault(ctype, [])
        if cname not in breakdown[ctype]:
            breakdown[ctype].append(cname)
    return breakdown


def format_business_rel(partner_role: pd.DataFrame, partner_id: str) -> List[Dict[str, str]]:
    records: List[Dict[str, str]] = []
    rows = partner_role[partner_role["partner_id"] == partner_id]
    for _, row in rows.iterrows():
        records.append(
            {
                "entity_type": row.get("entity_type"),
                "entity_id": row.get("entity_id"),
                "relationship_start_date": str(row.get("relationship_start_date")),
                "relationship_end_date": str(row.get("relationship_end_date")),
                "br_type_code": row.get("br_type_code"),
                "associated_partner_id": row.get("associated_partner_id"),
            }
        )
    return records


def associated_persons(partner_role: pd.DataFrame, partner_df: pd.DataFrame, partner_id: str) -> Dict[str, List[Dict[str, str]]]:
    """
    Capture associated persons (outgoing and incoming associations) using associated_partner_id.
    """
    result = {"linked_from_partner": [], "linked_to_partner": []}

    # Links where the current partner points to others
    rows_out = partner_role[(partner_role["partner_id"] == partner_id) & partner_role["associated_partner_id"].notna()]
    for _, row in rows_out.iterrows():
        assoc_id = row["associated_partner_id"]
        name = partner_df[partner_df["partner_id"] == assoc_id]["partner_name"].iloc[0] if (partner_df["partner_id"] == assoc_id).any() else None
        result["linked_from_partner"].append(
            {
                "associated_partner_id": assoc_id,
                "associated_partner_name": name,
                "br_type_code": row.get("br_type_code"),
                "relationship_start_date": row.get("relationship_start_date"),
                "relationship_end_date": row.get("relationship_end_date"),
            }
        )

    # Links where others point to this partner
    rows_in = partner_role[(partner_role["associated_partner_id"] == partner_id)]
    for _, row in rows_in.iterrows():
        origin_id = row["partner_id"]
        name = partner_df[partner_df["partner_id"] == origin_id]["partner_name"].iloc[0] if (partner_df["partner_id"] == origin_id).any() else None
        result["linked_to_partner"].append(
            {
                "partner_id": origin_id,
                "partner_name": name,
                "br_type_code": row.get("br_type_code"),
                "relationship_start_date": row.get("relationship_start_date"),
                "relationship_end_date": row.get("relationship_end_date"),
            }
        )

    # Remove empty buckets
    return {k: v for k, v in result.items() if v}


def is_basic_question(question: str) -> bool:
    lowered = question.lower()
    keywords = ["info", "information", "who is", "tell me about", "basic", "give me", "details on"]
    return any(k in lowered for k in keywords) and len(lowered.split()) <= 25


@dataclass
class PartnerResolution:
    partner_id: Optional[str]
    account_ids: List[str]
    partner_name: Optional[str]
    match_reason: str


class AccountAgent:
    def __init__(self, model: str = "openai/gpt-oss-120b", temperature: float = 0.0, verbose: bool = False) -> None:
        self.model_name = model
        self.temperature = temperature
        self.verbose = verbose
        if Together is None:
            self.client = _MockClient()
            self.using_mock_llm = True
        else:
            self.client = Together()
            self.using_mock_llm = False

        self.partner_df = load_partner_core()
        self.partner_country_df = load_partner_country()
        self.onboarding_df = load_onboarding_notes()
        self.watchlist_df = load_watchlist(partner_class="I")
        self.partner_role_df, self.business_rel_df = load_relationships()
        self.br_to_account_df, self.account_df = load_account_mapping()
        self.transactions_df, self.accounts_df = load_feature_data()
        self.tx_for_countries = load_tx_for_countries(find_tx_file_for_countries())
        self.suspicious_industries = load_suspicious_industries()
        self.account_to_partner, self.partner_to_accounts = self._build_account_partner_maps()
        self.system_prompt = (
            "You are an AML account information agent. Use ONLY the provided context. "
            "If watchlist_warning is present, surface it prominently. "
            "If basic_request is true, respond using this exact structure:\n"
            "- Summary: <concise resume with the person's name + onboarding description>\n"
            "- Industry: <industry>; suspicious_industry: <yes/no>\n"
            "- Countries: residence=<country_of_residence>; outgoing={list of country:amount}\n"
            "- Business relationship: <key relationship facts>\n"
            "Otherwise, answer concisely and select only the most relevant feature metrics for the question. "
            "Never invent values; say 'Not available' when data is missing."
        )

    def _build_account_partner_maps(self) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
        partner_br = self.partner_role_df[self.partner_role_df["entity_type"] == "BR"][["partner_id", "entity_id"]]
        partner_br.columns = ["partner_id", "br_id"]
        mapping = self.br_to_account_df.merge(partner_br, on="br_id", how="left")

        account_to_partner: Dict[str, str] = {}
        partner_to_accounts: Dict[str, List[str]] = {}
        for _, row in mapping.iterrows():
            raw_account = row.get("account_id")
            raw_partner = row.get("partner_id")
            if pd.isna(raw_account) or pd.isna(raw_partner):
                continue
            account_id = str(raw_account)
            partner_id = str(raw_partner)
            account_to_partner[account_id] = partner_id
            partner_to_accounts.setdefault(partner_id, []).append(account_id)
        return account_to_partner, partner_to_accounts

    def _best_name_match(self, question: str) -> Optional[str]:
        q_norm = _normalize(question)
        best_score = 0.0
        best_id: Optional[str] = None
        for _, row in self.partner_df.iterrows():
            name = row.get("partner_name", "")
            score = _similarity(q_norm, _normalize(name))
            if score > best_score:
                best_score = score
                best_id = row["partner_id"]
        if best_score >= 0.55:
            return best_id
        return None

    def _name_in_question(self, question: str) -> Optional[str]:
        """
        Try to pull an explicit partner name mention out of the user question.
        Prefers the longest fully matched name.
        """
        q_tokens = set(_normalize(question).split())
        best_id: Optional[str] = None
        best_len = 0
        for _, row in self.partner_df.iterrows():
            name_tokens = [t for t in _normalize(row.get("partner_name", "")).split() if t]
            if not name_tokens:
                continue
            if all(tok in q_tokens for tok in name_tokens) and len(name_tokens) > best_len:
                best_id = row["partner_id"]
                best_len = len(name_tokens)
        return best_id

    def resolve_partner(self, question: str) -> PartnerResolution:
        uuid_candidates = re.findall(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", question)
        for candidate in uuid_candidates:
            if candidate in set(self.partner_df["partner_id"]):
                return PartnerResolution(candidate, self.partner_to_accounts.get(candidate, []), None, "partner_id match")
            if candidate in self.account_to_partner:
                pid = self.account_to_partner[candidate]
                return PartnerResolution(pid, [candidate], None, "account_id matched to partner")

        direct_name = self._name_in_question(question)
        if direct_name:
            return PartnerResolution(direct_name, self.partner_to_accounts.get(direct_name, []), None, "name in question")

        name_match = self._best_name_match(question)
        if name_match:
            return PartnerResolution(name_match, self.partner_to_accounts.get(name_match, []), None, "fuzzy name match")

        return PartnerResolution(None, [], None, "not_found")

    def _watchlist_entry(self, partner_id: str) -> Optional[Dict[str, str]]:
        row = self.watchlist_df[self.watchlist_df["partner_id"] == partner_id]
        if row.empty:
            return None
        return row.iloc[0].to_dict()

    def _onboarding_note(self, partner_id: str) -> Optional[str]:
        note = self.onboarding_df[self.onboarding_df["Partner_ID"] == partner_id]
        if note.empty:
            return None
        return note.iloc[0].get("Onboarding_Note")

    def _build_resume(self, partner_id: str, partner_name: Optional[str], onboarding_note: Optional[str]) -> str:
        """
        Build a concise resume string combining name + onboarding note.
        """
        name = partner_name or self.partner_df[self.partner_df["partner_id"] == partner_id].iloc[0].get("partner_name")
        note = onboarding_note or "Not available"
        resume = f"{name}: {note}" if name else note
        if len(resume) > 300:
            resume = resume[:297].rstrip() + "..."
        return resume

    def _data_completeness(self, tx_df: pd.DataFrame) -> Dict:
        required_cols = ["Date", "Amount", "ext_counterparty_country", "counterparty_account_id", "ext_counterparty_account_id", "Debit/Credit"]
        present = [c for c in required_cols if c in tx_df.columns]
        missing = [c for c in required_cols if c not in tx_df.columns]
        score = round(len(present) / len(required_cols), 2)
        return {"required_columns": required_cols, "present": present, "missing": missing, "completeness_score": score}

    def _tx_stats(self, tx_df: pd.DataFrame) -> Dict:
        if tx_df.empty or "Date" not in tx_df.columns:
            return {"tx_count": 0}
        start = tx_df["Date"].min()
        end = tx_df["Date"].max()
        tx_count = len(tx_df)
        return {"tx_count": tx_count, "start_date": str(start.date()), "end_date": str(end.date())}

    def _outgoing_countries(self, account_ids: List[str]) -> List[Dict[str, float]]:
        aggregated: Dict[str, float] = {}
        for acc in account_ids:
            grouped, _, _ = amount_sent_per_country(self.tx_for_countries, account_id=acc, window_days=None)
            for _, row in grouped.iterrows():
                country = row["country_clean"]
                aggregated[country] = aggregated.get(country, 0.0) + float(row["total_sent"])
        pairs = [{"country": c, "total_sent": v} for c, v in aggregated.items()]
        pairs.sort(key=lambda x: x["total_sent"], reverse=True)
        return pairs

    def _is_suspicious_industry(self, industry: str) -> bool:
        return industry in self.suspicious_industries

    def _compress_features(self, analysis: Dict) -> Dict:
        if not analysis:
            return {}
        slim_features = []
        for feat in analysis.get("features", []):
            slim_features.append(
                {
                    "feature_name": feat.get("feature_name"),
                    "risk_level": feat.get("risk_level"),
                    "risk_score": feat.get("risk_score"),
                    "risk_reasons": feat.get("risk_reasons"),
                    "key_metrics": {k: v for k, v in (feat.get("metrics") or {}).items() if isinstance(v, (int, float, str, list, dict))},
                }
            )
        return {
            "summary": analysis.get("summary"),
            "features": slim_features,
        }

    def _basic_profile(self, partner_id: str) -> Dict:
        row = self.partner_df[self.partner_df["partner_id"] == partner_id].iloc[0].to_dict()
        industry = row.get("industry_gic2_code")
        countries = country_breakdown(self.partner_country_df, partner_id)
        return {
            "partner_id": partner_id,
            "partner_name": row.get("partner_name"),
            "gender": row.get("partner_gender"),
            "birth": str(row.get("partner_birth_year")),
            "phone": row.get("partner_phone_number"),
            "address": row.get("partner_address"),
            "open_date": str(row.get("partner_open_date")),
            "close_date": str(row.get("partner_close_date")),
            "industry": industry,
            "suspicious_industry": self._is_suspicious_industry(industry),
            "country_domicile": countries.get("domicile"),
            "country_tax": countries.get("tax"),
            "country_mailing": countries.get("mailing"),
        }

    def answer(self, question: str) -> str:
        resolution = self.resolve_partner(question)
        if not resolution.partner_id:
            return "Could not identify the partner/account from the question."

        partner_id = resolution.partner_id
        partner_name = self.partner_df[self.partner_df["partner_id"] == partner_id].iloc[0].get("partner_name")
        profile = self._basic_profile(partner_id)
        watchlist_info = self._watchlist_entry(partner_id)
        onboarding_note = self._onboarding_note(partner_id)
        country_of_res = pick_country_of_residence(self.partner_country_df, partner_id)
        profile["country_of_residence"] = country_of_res

        outgoing = self._outgoing_countries(resolution.account_ids or self.partner_to_accounts.get(partner_id, []))
        relationships = format_business_rel(self.partner_role_df, partner_id)
        associations = associated_persons(self.partner_role_df, self.partner_df, partner_id)
        resume = self._build_resume(partner_id, partner_name, onboarding_note)

        # Compute AML features with stdout muted to avoid clutter.
        with redirect_stdout(io.StringIO()):
            features_analysis = run_all_features(
                self.transactions_df,
                self.accounts_df,
                partner_id=partner_id,
                partner_name=partner_name,
                save_json=False,
            )
        compressed_features = self._compress_features(features_analysis)
        summary_meta = features_analysis.get("summary") if features_analysis else {}
        overall_risk_level = "LOW"
        if summary_meta:
            if summary_meta.get("high_risk_features", 0) > 0:
                overall_risk_level = "HIGH"
            elif summary_meta.get("medium_risk_features", 0) > 0:
                overall_risk_level = "MEDIUM"
        overall_risk_score = summary_meta.get("average_risk_score") if summary_meta else None

        partner_txs = self.transactions_df[self.transactions_df["partner_id"] == partner_id]
        tx_stats = self._tx_stats(partner_txs)
        completeness = self._data_completeness(partner_txs)

        basic_flag = is_basic_question(question)
        watchlist_warning = ""
        if watchlist_info:
            rank = watchlist_info.get("watch_rank")
            risk_level = watchlist_info.get("overall_risk_level")
            score = watchlist_info.get("aggregate_risk_score")
            details = []
            if rank:
                details.append(f"rank {int(rank)}")
            if risk_level:
                details.append(f"risk={risk_level}")
            if score is not None and not pd.isna(score):
                details.append(f"score={score}")
            suffix = f" ({', '.join(details)})" if details else ""
            reason = watchlist_info.get("watch_reason") or "Flagged in top suspects list."
            watchlist_warning = f"⚠️ Partner is on suspects list{suffix}: {reason}"

        user_content = (
            f"Question: {question}\n"
            f"Basic request: {basic_flag}\n"
            f"Header: client={partner_name} ({partner_id}); overall_risk_level={overall_risk_level}; overall_risk_score={overall_risk_score}; tx_stats={tx_stats}\n"
            f"Partner profile: {json.dumps(profile, ensure_ascii=False, indent=2)}\n"
            f"Watchlist warning: {watchlist_warning or 'None'}\n"
            f"Outgoing countries: {json.dumps(outgoing, ensure_ascii=False, indent=2)}\n"
            f"Business relationships: {json.dumps(relationships, ensure_ascii=False, indent=2)}\n"
            f"Associated persons: {json.dumps(associations, ensure_ascii=False, indent=2)}\n"
            f"AML features: {json.dumps(compressed_features if self.verbose else compressed_features.get('summary'), ensure_ascii=False, indent=2)}\n"
            f"Onboarding note: {onboarding_note or 'Not available'}\n"
            f"Onboarding resume: {resume}\n"
            f"Data completeness: {json.dumps(completeness, ensure_ascii=False, indent=2)}\n"
            "Provide the answer now."
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                temperature=self.temperature,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_content},
                ],
            )
            content = response.choices[0].message.content
        except Exception as exc:  # pragma: no cover - runtime guard
            content = f"[llm_error] {exc}"

        preface = watchlist_warning + ("\n" if watchlist_warning else "")
        if getattr(self, "using_mock_llm", False):
            preface += "[using mock Together client for offline test]\n"
        return preface + content


def main() -> None:
    parser = argparse.ArgumentParser(description="Account information agent (Together.ai).")
    parser.add_argument("question", help="Question to ask about an account/partner.")
    parser.add_argument("--model", default="openai/gpt-oss-120b", help="Together model name.")
    parser.add_argument("--temperature", type=float, default=0.0, help="LLM temperature.")
    parser.add_argument("--verbose", action="store_true", help="Include full feature details in the prompt.")
    args = parser.parse_args()

    agent = AccountAgent(model=args.model, temperature=args.temperature, verbose=args.verbose)
    print(agent.answer(args.question))


if __name__ == "__main__":
    main()
