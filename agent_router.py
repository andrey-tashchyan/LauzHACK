"""
Agent router that classifies a user question and dispatches to the right specialist.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional, Iterator

from utils.router import RouteQuery, create_route_chain
from utils.session_manager import ConversationSession, get_session_manager

try:
    from company_agent import CompanyQAAgent
except Exception:
    CompanyQAAgent = None  # type: ignore


ROOT = Path(__file__).resolve().parent
FEATURE_TERMS = {
    "feature",
    "aml feature",
    "transaction frequency",
    "frequency",
    "burst",
    "structuring",
    "atypical",
    "cross border",
    "cross-border",
    "counterparty",
    "counterparties",
    "irregularity",
    "night activity",
    "ephemeral",
    "abnormal activity",
    "account age",
    "multiplicity",
}


class AgentRouter:
    """
    Routes questions to the appropriate downstream agent.
    """

    def __init__(
        self,
        model: str = "openai/gpt-oss-120b",
        company_model: Optional[str] = None,
    ) -> None:
        self.model = model
        self.company_model = company_model or model
        self.route_chain = create_route_chain(model=model)
        self._company_agent: Optional[Any] = None

    def _is_feature_request(self, question: str) -> bool:
        """
        Heuristic to shortcut routing when the user explicitly asks for AML features.
        """
        lowered = question.lower()
        return any(term in lowered for term in FEATURE_TERMS)

    def _run_script(self, script_name: str, question: str) -> str:
        """
        Execute a sibling Python script with the question as CLI argument.
        """
        script_path = ROOT / script_name
        if not script_path.exists():
            return f"[Router] Missing agent script: {script_path}"

        completed = subprocess.run(
            [sys.executable, str(script_path), question],
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            stderr = completed.stderr.strip()
            stdout = completed.stdout.strip()
            return (
                f"[Router] {script_name} failed (exit {completed.returncode}). "
                f"{stderr or stdout}"
            )
        return completed.stdout.strip() or f"[Router] {script_name} returned no output."

    def _run_company_agent(
        self,
        question: str,
        session: Optional[ConversationSession] = None
    ) -> str:
        """
        Use the in-process CompanyQAAgent when available.
        """
        if CompanyQAAgent is None:
            return "[Router] company_agent.py is unavailable in this environment."

        if self._company_agent is None:
            self._company_agent = CompanyQAAgent(model=self.company_model)

        return self._company_agent.answer(question, session=session)

    def _run_company_agent_stream(
        self,
        question: str,
        session: Optional[ConversationSession] = None
    ) -> Iterator[str]:
        """
        Stream response from CompanyQAAgent.
        """
        if CompanyQAAgent is None:
            yield "[Router] company_agent.py is unavailable in this environment."
            return

        if self._company_agent is None:
            self._company_agent = CompanyQAAgent(model=self.company_model)

        yield from self._company_agent.answer_stream(question, session=session)

    def route_and_execute(
        self,
        question: str,
        session: Optional[ConversationSession] = None
    ) -> str:
        """
        Route a question, then dispatch to the matched agent.

        Args:
            question: User's question
            session: Optional conversation session for context
        """
        # Shortcut: explicit feature questions should go to account_agent directly
        feature_override = self._is_feature_request(question)
        if feature_override:
            route_result = RouteQuery(destination="account_info", task="account_feature_analysis", confidence=1.0)
            destination = "account_info"
            task = "account_feature_analysis"
        else:
            try:
                route_result = self.route_chain.invoke({"question": question})
                print(f"DEBUG: route_result = {route_result}")  # Debug logging
            except Exception as exc:  # pragma: no cover - defensive guard
                return f"[routing_error] Failed to classify request: {exc}"

            if route_result is None:
                return "[routing_error] The routing model returned None. Please try again."

            destination = route_result.destination
            task = route_result.task

        # Store routing decision in session
        if session:
            session.add_message("user", question)
            session.set_context("last_destination", destination)
            session.set_context("last_task", task)

        if destination == "suspicious_activity":
            body = self._run_script("suspicious_agent.py", question)
        elif destination == "company_info":
            body = self._run_company_agent(question, session)
        elif destination == "account_info":
            body = self._run_script("account_agent.py", question)
        else:
            body = (
                "The request does not match the supported tasks "
                "(suspicious activity, company information, account activity)."
            )

        # Store response in session
        if session:
            session.add_message(
                "assistant",
                body,
                destination=destination,
                task=task
            )

        return f"[{destination}:{task}] {body}"

    def route_and_execute_stream(
        self,
        question: str,
        session: Optional[ConversationSession] = None
    ) -> Iterator[str]:
        """
        Route a question and stream the response from the matched agent.

        Args:
            question: User's question
            session: Optional conversation session for context

        Yields:
            Response chunks as they arrive
        """
        feature_override = self._is_feature_request(question)
        if feature_override:
            route_result = RouteQuery(destination="account_info", task="account_feature_analysis", confidence=1.0)
            destination = "account_info"
            task = "account_feature_analysis"
        else:
            try:
                route_result = self.route_chain.invoke({"question": question})
                print(f"DEBUG: route_result = {route_result}")
            except Exception as exc:
                yield f"[routing_error] Failed to classify request: {exc}"
                return

            if route_result is None:
                yield "[routing_error] The routing model returned None. Please try again."
                return

            destination = route_result.destination
            task = route_result.task

        # Store routing decision
        if session:
            session.add_message("user", question)
            session.set_context("last_destination", destination)
            session.set_context("last_task", task)

        # Yield the routing header
        yield f"[{destination}:{task}] "

        # Stream from the appropriate agent
        full_response = ""
        if destination == "company_info":
            # Company agent supports streaming
            for chunk in self._run_company_agent_stream(question, session):
                full_response += chunk
                yield chunk
        else:
            # Fallback to non-streaming for other agents
            if destination == "suspicious_activity":
                body = self._run_script("suspicious_agent.py", question)
            elif destination == "account_info":
                body = self._run_script("account_agent.py", question)
            else:
                body = (
                    "The request does not match the supported tasks "
                    "(suspicious activity, company information, account activity)."
                )
            full_response = body
            yield body

        # Store complete response in session
        if session:
            session.add_message(
                "assistant",
                full_response,
                destination=destination,
                task=task
            )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Route a question to the correct agent and run it."
    )
    parser.add_argument("question", help="User question to route.")
    parser.add_argument(
        "--model",
        default="openai/gpt-oss-120b",
        help="Together model for routing (default: openai/gpt-oss-120b).",
    )
    parser.add_argument(
        "--company-model",
        dest="company_model",
        help="Optional model override for the company agent.",
    )
    args = parser.parse_args()

    router = AgentRouter(model=args.model, company_model=args.company_model)
    print(router.route_and_execute(args.question))


if __name__ == "__main__":
    main()
