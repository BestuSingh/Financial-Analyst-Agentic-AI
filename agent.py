"""Gemini-powered LangChain agent for financial analysis."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import InMemorySaver

from tools import FINANCIAL_TOOLS


SYSTEM_PROMPT = """You are Financial Analyst Agent, a senior-grade autonomous financial analysis assistant.

Use tools for market data, fundamentals, technical analysis, comparisons, charts, and report generation.
Do not invent prices, indicators, fundamentals, charts, or recommendations.

Reasoning policy:
- For a full stock report, call generate_financial_report.
- For indicator-specific questions, call run_technical_analysis with appropriate windows.
- For latest or historical price questions, call fetch_stock_data.
- For fundamentals or company context, call fetch_alpha_vantage_overview.
- For follow-ups like "compare it with last week", use conversation memory to resolve the prior ticker and call compare_recent_performance.
- For chart or visualization requests, call create_price_chart and share the generated file path.
- If a tool reports a recoverable failure, continue with available data and state the limitation.
- Once the answer contains the requested metrics, stop calling tools and answer clearly.

Report style:
- Keep this format for financial reports:
  Financial Report for [TICKER]
  * Current Price:
  * Trend:
  * RSI:
  * Moving Averages:
  Analysis:
  Recommendation:
- Recommendations must be Buy, Hold, or Sell with reasoning.
- Always include a short risk note that this is analytical information, not personalized financial advice.
"""


class MissingConfigurationError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


class AgentRuntimeError(RuntimeError):
    """Raised when the running agent fails in a user-fixable way."""


PLACEHOLDER_API_KEYS = {
    "your_gemini_api_key",
    "paste_your_real_gemini_key_here",
    "your_google_api_key",
}


def clean_env_value(value: str | None) -> str | None:
    """Strip spaces and accidental quotes from .env values."""

    if value is None:
        return None
    cleaned = value.strip().strip('"').strip("'").strip()
    return cleaned or None


@dataclass
class AgentConfig:
    """Runtime configuration for the Financial Analyst Agent."""

    model: str = "gemini-2.5-flash"
    temperature: float = 0.0
    api_key: str | None = None

    @classmethod
    def from_env(cls) -> "AgentConfig":
        """Load configuration from environment variables."""

        load_dotenv(override=True)
        return cls(
            model=clean_env_value(os.getenv("GEMINI_MODEL")) or "gemini-2.5-flash",
            temperature=float(clean_env_value(os.getenv("GEMINI_TEMPERATURE")) or "0"),
            api_key=clean_env_value(os.getenv("GEMINI_API_KEY"))
            or clean_env_value(os.getenv("GOOGLE_API_KEY")),
        )

    def validate(self) -> None:
        """Validate required settings before creating the model."""

        if not self.api_key:
            raise MissingConfigurationError(
                "GEMINI_API_KEY is required. Create a .env file from .env.example and paste your real Gemini key."
            )
        if self.api_key.lower() in PLACEHOLDER_API_KEYS:
            raise MissingConfigurationError(
                "GEMINI_API_KEY is still set to the placeholder value. Replace it in .env with your real Gemini API key."
            )


class FinancialAnalystAgent:
    """LangChain agent with Gemini, tools, and conversational memory."""

    def __init__(self, config: AgentConfig | None = None) -> None:
        self.config = config or AgentConfig.from_env()
        self.config.validate()
        self.checkpointer = InMemorySaver()
        self.model = ChatGoogleGenerativeAI(
            model=self.config.model,
            temperature=self.config.temperature,
            api_key=self.config.api_key,
            timeout=60,
            max_retries=2,
        )
        self.agent = create_agent(
            model=self.model,
            tools=FINANCIAL_TOOLS,
            system_prompt=SYSTEM_PROMPT,
            checkpointer=self.checkpointer,
        )

    def run(self, user_message: str, session_id: str = "default") -> str:
        """Invoke the agent and return the final assistant message."""

        try:
            response: dict[str, Any] = self.agent.invoke(
                {"messages": [{"role": "user", "content": user_message}]},
                config={"configurable": {"thread_id": session_id}},
            )
        except Exception as exc:
            message = str(exc)
            if "API key not valid" in message or "API_KEY_INVALID" in message:
                raise AgentRuntimeError(
                    "Gemini rejected your API key. Open .env and replace GEMINI_API_KEY with a valid key from Google AI Studio."
                ) from exc
            raise

        messages = response.get("messages", [])
        if not messages:
            return str(response)

        final_message = messages[-1]
        text_attr = getattr(final_message, "text", None)
        if isinstance(text_attr, str) and text_attr:
            return text_attr
        if callable(text_attr):
            try:
                text = text_attr()
                if text:
                    return str(text)
            except Exception:
                pass

        content = getattr(final_message, "content", final_message)
        if isinstance(content, list):
            text_blocks = [
                item.get("text", "")
                for item in content
                if isinstance(item, dict) and item.get("type") == "text"
            ]
            if text_blocks:
                return "\n".join(text_blocks)
            return "\n".join(str(item) for item in content)
        return str(content)
