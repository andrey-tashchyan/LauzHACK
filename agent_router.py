"""
Agent router that classifies a user question and dispatches to the right specialist.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

from utils.router import RouteQuery, create_route_chain

try:
    from company_agent import CompanyQAAgent
except Exception:
    CompanyQAAgent = None  # type: ignore


ROOT = Path(__file__).resolve().parent


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

    def _run_company_agent(self, question: str) -> str:
        """
        Use the in-process CompanyQAAgent when available.
        """
        if CompanyQAAgent is None:
            return "[Router] company_agent.py is unavailable in this environment."

        if self._company_agent is None:
            self._company_agent = CompanyQAAgent(model=self.company_model)

        return self._company_agent.answer(question)

    def route_and_execute(self, question: str) -> str:
        """
        Route a question, then dispatch to the matched agent.
        """
        try:
            route_result: RouteQuery = self.route_chain.invoke({"question": question})
            print(f"DEBUG: route_result = {route_result}")  # Debug logging
        except Exception as exc:  # pragma: no cover - defensive guard
            return f"[routing_error] Failed to classify request: {exc}"

        if route_result is None:
            return "[routing_error] The routing model returned None. Please try again."

        destination = route_result.destination
        task = route_result.task

        if destination == "suspicious_activity":
            body = self._run_script("suspicious_agent.py", question)
        elif destination == "company_info":
            body = self._run_company_agent(question)
        elif destination == "account_info":
            body = self._run_script("account_agent.py", question)
        else:
            body = (
                "The request does not match the supported tasks "
                "(suspicious activity, company information, account activity)."
            )

        return f"[{destination}:{task}] {body}"


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
