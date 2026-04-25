"""LangChain tools for financial data, analysis, charts, and reports."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import requests
import yfinance as yf
from langchain_core.tools import tool

from analysis import (
    analyze_prices,
    build_report,
    exponential_moving_average,
    normalize_ohlcv_frame,
    simple_moving_average,
    summarize_price_history,
)


DEFAULT_CACHE_TTL_SECONDS = int(os.getenv("FINANCIAL_AGENT_CACHE_TTL_SECONDS", "300"))


@dataclass
class CacheEntry:
    """Simple TTL cache entry."""

    value: Any
    expires_at: float


class TTLCache:
    """Small in-memory TTL cache for repeated API calls."""

    def __init__(self, ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS) -> None:
        self.ttl_seconds = ttl_seconds
        self._items: dict[str, CacheEntry] = {}

    def get(self, key: str) -> Any | None:
        """Return a cached value if it has not expired."""

        entry = self._items.get(key)
        if entry is None:
            return None
        if entry.expires_at < time.time():
            self._items.pop(key, None)
            return None
        return entry.value

    def set(self, key: str, value: Any) -> None:
        """Store a value with the configured TTL."""

        self._items[key] = CacheEntry(value=value, expires_at=time.time() + self.ttl_seconds)


MARKET_DATA_CACHE = TTLCache()
ALPHA_VANTAGE_CACHE = TTLCache()


def success_payload(**data: Any) -> str:
    """Return a consistent JSON success payload."""

    return json.dumps({"ok": True, **data}, indent=2, default=str)


def error_payload(message: str, **data: Any) -> str:
    """Return a consistent JSON error payload."""

    return json.dumps({"ok": False, "error": message, **data}, indent=2, default=str)


def normalize_ticker(ticker: str) -> str:
    """Normalize user-supplied ticker symbols."""

    cleaned = ticker.strip().upper()
    if not cleaned:
        raise ValueError("Ticker cannot be empty.")
    return cleaned


def get_cached_or_fetch_history(ticker: str, period: str = "6mo", interval: str = "1d") -> tuple[pd.DataFrame, dict[str, Any]]:
    """Fetch yfinance data with TTL caching."""

    normalized_ticker = normalize_ticker(ticker)
    cache_key = f"yf:{normalized_ticker}:{period}:{interval}"
    cached = MARKET_DATA_CACHE.get(cache_key)
    if cached is not None:
        return cached["frame"].copy(), cached["metadata"]

    ticker_client = yf.Ticker(normalized_ticker)
    frame = ticker_client.history(period=period, interval=interval, auto_adjust=False)
    cleaned = normalize_ohlcv_frame(frame)

    info: dict[str, Any] = {"currency": "USD"}
    try:
        fast_info = getattr(ticker_client, "fast_info", {}) or {}
        info = {
            "currency": fast_info.get("currency") or "USD",
            "previous_close": fast_info.get("previous_close"),
            "market_cap": fast_info.get("market_cap"),
        }
    except Exception:
        info = {"currency": "USD"}

    metadata = {
        "ticker": normalized_ticker,
        "period": period,
        "interval": interval,
        "currency": info.get("currency") or "USD",
        "rows": len(cleaned),
        "first_date": str(cleaned["Date"].iloc[0]),
        "last_date": str(cleaned["Date"].iloc[-1]),
        "current_price": float(cleaned["Close"].iloc[-1]),
        "previous_close": info.get("previous_close"),
        "market_cap": info.get("market_cap"),
    }
    MARKET_DATA_CACHE.set(cache_key, {"frame": cleaned.copy(), "metadata": metadata})
    return cleaned, metadata


def get_alpha_vantage_overview(ticker: str) -> dict[str, Any]:
    """Fetch company overview data from Alpha Vantage."""

    normalized_ticker = normalize_ticker(ticker)
    cache_key = f"alpha:overview:{normalized_ticker}"
    cached = ALPHA_VANTAGE_CACHE.get(cache_key)
    if cached is not None:
        return cached

    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key or api_key == "your_alpha_vantage_key":
        payload = {
            "ok": False,
            "ticker": normalized_ticker,
            "error": "ALPHA_VANTAGE_API_KEY is not set. Continuing without Alpha Vantage fundamentals.",
        }
        ALPHA_VANTAGE_CACHE.set(cache_key, payload)
        return payload

    try:
        response = requests.get(
            "https://www.alphavantage.co/query",
            params={"function": "OVERVIEW", "symbol": normalized_ticker, "apikey": api_key},
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        payload = {"ok": False, "ticker": normalized_ticker, "error": f"Alpha Vantage request failed: {exc}"}
        ALPHA_VANTAGE_CACHE.set(cache_key, payload)
        return payload

    if not data:
        payload = {"ok": False, "ticker": normalized_ticker, "error": "Alpha Vantage returned no overview data."}
    elif "Note" in data:
        payload = {"ok": False, "ticker": normalized_ticker, "error": f"Alpha Vantage service note: {data['Note']}"}
    elif "Information" in data:
        payload = {"ok": False, "ticker": normalized_ticker, "error": f"Alpha Vantage information: {data['Information']}"}
    else:
        payload = {
            "ok": True,
            "ticker": normalized_ticker,
            "name": data.get("Name"),
            "description": data.get("Description"),
            "sector": data.get("Sector"),
            "industry": data.get("Industry"),
            "market_capitalization": data.get("MarketCapitalization"),
            "pe_ratio": data.get("PERatio"),
            "eps": data.get("EPS"),
            "profit_margin": data.get("ProfitMargin"),
            "analyst_target_price": data.get("AnalystTargetPrice"),
            "dividend_yield": data.get("DividendYield"),
        }

    ALPHA_VANTAGE_CACHE.set(cache_key, payload)
    return payload


@tool
def fetch_stock_data(ticker: str, period: str = "6mo", interval: str = "1d") -> str:
    """Fetch historical and latest stock price data from yfinance."""

    try:
        frame, metadata = get_cached_or_fetch_history(ticker, period=period, interval=interval)
        return success_payload(source="yfinance", metadata=metadata, recent_prices=summarize_price_history(frame))
    except Exception as exc:
        return error_payload(f"Unable to fetch yfinance data: {exc}", ticker=ticker, period=period, interval=interval)


@tool
def fetch_alpha_vantage_overview(ticker: str) -> str:
    """Fetch company fundamentals and overview data from Alpha Vantage."""

    try:
        return json.dumps(get_alpha_vantage_overview(ticker), indent=2, default=str)
    except Exception as exc:
        return error_payload(f"Unable to fetch Alpha Vantage overview: {exc}", ticker=ticker)


@tool
def run_technical_analysis(
    ticker: str,
    period: str = "6mo",
    interval: str = "1d",
    sma_short_window: int = 20,
    sma_long_window: int = 50,
    ema_window: int = 20,
    rsi_period: int = 14,
) -> str:
    """Run SMA, EMA, RSI, trend detection, volatility, and recommendation logic."""

    try:
        frame, metadata = get_cached_or_fetch_history(ticker, period=period, interval=interval)
        snapshot = analyze_prices(
            ticker=ticker,
            frame=frame,
            currency=metadata.get("currency", "USD"),
            sma_short_window=sma_short_window,
            sma_long_window=sma_long_window,
            ema_window=ema_window,
            rsi_period=rsi_period,
        )
        return success_payload(source="internal_analysis", analysis=snapshot.to_dict())
    except Exception as exc:
        return error_payload(f"Unable to run technical analysis: {exc}", ticker=ticker, period=period, interval=interval)


@tool
def generate_financial_report(ticker: str, period: str = "6mo", interval: str = "1d") -> str:
    """Generate a structured report with summary, metrics, trend, and recommendation."""

    try:
        frame, metadata = get_cached_or_fetch_history(ticker, period=period, interval=interval)
        snapshot = analyze_prices(ticker=ticker, frame=frame, currency=metadata.get("currency", "USD"))
        overview = get_alpha_vantage_overview(ticker)
        company_name = overview.get("name") if overview.get("ok") else None
        sector = overview.get("sector") if overview.get("ok") else None
        alpha_note = None if overview.get("ok") else overview.get("error")
        return build_report(snapshot=snapshot, company_name=company_name, sector=sector, alpha_vantage_note=alpha_note)
    except Exception as exc:
        return error_payload(f"Unable to generate report: {exc}", ticker=ticker, period=period, interval=interval)


@tool
def compare_recent_performance(ticker: str, lookback_days: int = 7, period: str = "1mo") -> str:
    """Compare latest close with the close from roughly N trading days ago."""

    try:
        if lookback_days < 1:
            raise ValueError("lookback_days must be at least 1.")

        frame, metadata = get_cached_or_fetch_history(ticker, period=period, interval="1d")
        normalized = normalize_ohlcv_frame(frame)
        if len(normalized) <= lookback_days:
            raise ValueError(
                f"Only {len(normalized)} rows are available, which is not enough for a {lookback_days}-day comparison."
            )

        latest = normalized.iloc[-1]
        prior = normalized.iloc[-(lookback_days + 1)]
        latest_close = float(latest["Close"])
        prior_close = float(prior["Close"])
        change = latest_close - prior_close
        pct_change = change / prior_close if prior_close else 0.0

        return success_payload(
            source="internal_analysis",
            ticker=metadata["ticker"],
            latest_date=latest["Date"],
            latest_close=round(latest_close, 2),
            prior_date=prior["Date"],
            prior_close=round(prior_close, 2),
            absolute_change=round(change, 2),
            percent_change=round(pct_change * 100, 2),
            interpretation=(
                "Price improved over the comparison window."
                if change > 0
                else "Price declined over the comparison window."
                if change < 0
                else "Price was flat over the comparison window."
            ),
        )
    except Exception as exc:
        return error_payload(f"Unable to compare recent performance: {exc}", ticker=ticker, lookback_days=lookback_days)


@tool
def create_price_chart(ticker: str, period: str = "6mo", interval: str = "1d") -> str:
    """Create an interactive Plotly HTML chart with close price, SMA 20, SMA 50, and EMA 20."""

    try:
        frame, metadata = get_cached_or_fetch_history(ticker, period=period, interval=interval)
        normalized = normalize_ohlcv_frame(frame)
        close = normalized["Close"].astype(float)
        normalized["SMA_20"] = simple_moving_average(close, 20)
        normalized["SMA_50"] = simple_moving_average(close, 50)
        normalized["EMA_20"] = exponential_moving_average(close, 20)

        figure = go.Figure()
        figure.add_trace(go.Scatter(x=normalized["Date"], y=normalized["Close"], mode="lines", name="Close"))
        figure.add_trace(go.Scatter(x=normalized["Date"], y=normalized["SMA_20"], mode="lines", name="SMA 20"))
        figure.add_trace(go.Scatter(x=normalized["Date"], y=normalized["SMA_50"], mode="lines", name="SMA 50"))
        figure.add_trace(go.Scatter(x=normalized["Date"], y=normalized["EMA_20"], mode="lines", name="EMA 20"))
        figure.update_layout(
            title=f"{metadata['ticker']} Price Trend ({period}, {interval})",
            xaxis_title="Date",
            yaxis_title=f"Price ({metadata.get('currency', 'USD')})",
            template="plotly_white",
            hovermode="x unified",
        )

        output_dir = Path.cwd() / "outputs" / "charts"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{metadata['ticker']}_{period}_{interval}_{int(time.time())}.html"
        figure.write_html(output_path, include_plotlyjs="cdn")

        return success_payload(
            source="plotly",
            ticker=metadata["ticker"],
            chart_path=str(output_path),
            chart_type="interactive_html",
            included_series=["Close", "SMA 20", "SMA 50", "EMA 20"],
        )
    except Exception as exc:
        return error_payload(f"Unable to create price chart: {exc}", ticker=ticker, period=period, interval=interval)


FINANCIAL_TOOLS = [
    fetch_stock_data,
    fetch_alpha_vantage_overview,
    run_technical_analysis,
    generate_financial_report,
    compare_recent_performance,
    create_price_chart,
]
