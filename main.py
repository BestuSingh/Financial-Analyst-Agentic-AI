"""CLI entry point for the Gemini-powered Financial Analyst Agent."""

from __future__ import annotations

import argparse
import sys

from agent import AgentRuntimeError, FinancialAnalystAgent, MissingConfigurationError


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line parser."""

    parser = argparse.ArgumentParser(description="Run the Agentic Financial Analyst Agent.")
    parser.add_argument("--ticker", help="Ticker symbol to analyze, e.g. AAPL or TSLA.")
    parser.add_argument("--question", help="Free-form user question for the agent.")
    parser.add_argument("--period", default="6mo", help="Historical period for reports, e.g. 1mo, 6mo, 1y.")
    parser.add_argument("--interval", default="1d", help="Price interval, e.g. 1d, 1wk, 1h.")
    parser.add_argument("--session-id", default="default", help="Conversation session id for memory.")
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Start an interactive session that preserves memory until you exit.",
    )
    return parser


def build_initial_prompt(args: argparse.Namespace) -> str:
    """Build the first prompt from CLI flags."""

    if args.question:
        return args.question
    if args.ticker:
        return f"Generate a financial report for {args.ticker} using period={args.period} and interval={args.interval}."
    return ""


def interactive_loop(agent: FinancialAnalystAgent, session_id: str) -> None:
    """Run an interactive session with memory."""

    print("Financial Analyst Agent interactive mode. Type 'exit' or 'quit' to stop.")
    while True:
        try:
            user_message = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            return

        if user_message.lower() in {"exit", "quit"}:
            print("Exiting.")
            return
        if not user_message:
            continue

        print("\nAgent:\n")
        try:
            print(agent.run(user_message, session_id=session_id))
        except AgentRuntimeError as exc:
            print(f"Agent error: {exc}")
        except Exception as exc:
            print(f"Unexpected error: {exc}")


def main() -> int:
    """Run the CLI."""

    parser = build_parser()
    args = parser.parse_args()

    try:
        agent = FinancialAnalystAgent()
    except MissingConfigurationError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    if args.interactive or not (args.ticker or args.question):
        interactive_loop(agent, session_id=args.session_id)
        return 0

    try:
        print(agent.run(build_initial_prompt(args), session_id=args.session_id))
        return 0
    except AgentRuntimeError as exc:
        print(f"Agent error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
