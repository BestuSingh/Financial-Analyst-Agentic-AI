"""Technical analysis and report helpers for the Financial Analyst Agent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


TRADING_DAYS_PER_YEAR = 252


@dataclass(frozen=True)
class TechnicalSnapshot:
    """A point-in-time technical analysis result."""

    ticker: str
    latest_date: str
    current_price: float
    currency: str
    sma_20: float | None
    sma_50: float | None
    ema_20: float | None
    rsi_14: float | None
    daily_volatility: float | None
    annualized_volatility: float | None
    trend: str
    momentum: str
    recommendation: str
    recommendation_reason: str

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-friendly values."""

        return {
            "ticker": self.ticker,
            "latest_date": self.latest_date,
            "current_price": round_float(self.current_price),
            "currency": self.currency,
            "sma_20": round_float(self.sma_20),
            "sma_50": round_float(self.sma_50),
            "ema_20": round_float(self.ema_20),
            "rsi_14": round_float(self.rsi_14),
            "daily_volatility": round_float(self.daily_volatility, 6),
            "annualized_volatility": round_float(self.annualized_volatility, 6),
            "trend": self.trend,
            "momentum": self.momentum,
            "recommendation": self.recommendation,
            "recommendation_reason": self.recommendation_reason,
        }


def round_float(value: float | int | None, digits: int = 2) -> float | None:
    """Round finite numeric values and keep missing values as None."""

    if value is None:
        return None
    if isinstance(value, (float, int, np.floating, np.integer)) and np.isfinite(value):
        return round(float(value), digits)
    return None


def normalize_ohlcv_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Clean yfinance OHLCV output into a stable DataFrame shape."""

    if frame is None or frame.empty:
        raise ValueError("No market data was returned for the requested ticker.")

    cleaned = frame.copy().dropna(how="all")
    if cleaned.empty:
        raise ValueError("Market data contained only empty rows.")

    cleaned.columns = [str(column).title().replace(" ", "_") for column in cleaned.columns]
    cleaned = cleaned.reset_index()
    cleaned.columns = [str(column).title().replace(" ", "_") for column in cleaned.columns]

    if "Date" not in cleaned.columns and "Datetime" in cleaned.columns:
        cleaned = cleaned.rename(columns={"Datetime": "Date"})
    if "Date" not in cleaned.columns:
        cleaned = cleaned.rename(columns={cleaned.columns[0]: "Date"})
    if "Close" not in cleaned.columns:
        raise ValueError("Market data is missing the Close price column.")

    cleaned["Date"] = pd.to_datetime(cleaned["Date"]).dt.strftime("%Y-%m-%d")
    for column in ["Open", "High", "Low", "Close", "Adj_Close", "Volume"]:
        if column in cleaned.columns:
            cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")

    cleaned = cleaned.dropna(subset=["Close"])
    if cleaned.empty:
        raise ValueError("Market data has no usable closing prices.")

    return cleaned


def simple_moving_average(close: pd.Series, window: int) -> pd.Series:
    """Calculate a simple moving average."""

    return close.rolling(window=window, min_periods=window).mean()


def exponential_moving_average(close: pd.Series, span: int) -> pd.Series:
    """Calculate an exponential moving average."""

    return close.ewm(span=span, adjust=False, min_periods=span).mean()


def relative_strength_index(close: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index using smoothed gains and losses."""

    delta = close.diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)
    avg_gain = gains.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = losses.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return (100 - (100 / (1 + rs))).fillna(50)


def calculate_volatility(close: pd.Series) -> tuple[float | None, float | None]:
    """Return daily and annualized volatility from percentage returns."""

    returns = close.pct_change().dropna()
    if returns.empty:
        return None, None
    daily = float(returns.std())
    annualized = daily * float(np.sqrt(TRADING_DAYS_PER_YEAR))
    return daily, annualized


def detect_trend(close: pd.Series, sma_20: float | None, sma_50: float | None) -> str:
    """Classify trend using moving averages and recent slope."""

    latest_close = float(close.iloc[-1])
    recent_window = close.tail(min(len(close), 20))
    slope = float(recent_window.iloc[-1] - recent_window.iloc[0]) if len(recent_window) > 1 else 0.0

    if sma_20 is None or sma_50 is None:
        if slope > 0:
            return "Bullish"
        if slope < 0:
            return "Bearish"
        return "Sideways"

    if latest_close > sma_20 > sma_50 and slope > 0:
        return "Bullish"
    if latest_close < sma_20 < sma_50 and slope < 0:
        return "Bearish"
    return "Sideways"


def classify_momentum(rsi_14: float | None) -> str:
    """Classify momentum from RSI."""

    if rsi_14 is None:
        return "Unknown"
    if rsi_14 >= 70:
        return "Overbought"
    if rsi_14 <= 30:
        return "Oversold"
    if rsi_14 >= 55:
        return "Positive"
    if rsi_14 <= 45:
        return "Negative"
    return "Neutral"


def choose_recommendation(
    trend: str,
    momentum: str,
    annualized_volatility: float | None,
    current_price: float,
    sma_20: float | None,
    sma_50: float | None,
) -> tuple[str, str]:
    """Create a conservative Buy/Hold/Sell signal from indicators."""

    high_volatility = annualized_volatility is not None and annualized_volatility >= 0.45
    above_averages = sma_20 is not None and sma_50 is not None and current_price > sma_20 and current_price > sma_50
    below_averages = sma_20 is not None and sma_50 is not None and current_price < sma_20 and current_price < sma_50

    if trend == "Bullish" and momentum in {"Positive", "Neutral"} and above_averages:
        if high_volatility:
            return (
                "Hold",
                "Trend is constructive, but elevated volatility argues for waiting for confirmation or using conservative sizing.",
            )
        return (
            "Buy",
            "Price is above key moving averages, trend is bullish, and RSI does not show an overbought extreme.",
        )

    if trend == "Bearish" and momentum in {"Negative", "Neutral"} and below_averages:
        return (
            "Sell",
            "Price is below key moving averages and momentum is weak, which keeps downside risk elevated.",
        )

    if momentum == "Overbought":
        return (
            "Hold",
            "Momentum is strong, but RSI is overbought, so a pullback or consolidation is plausible.",
        )

    if momentum == "Oversold" and trend != "Bearish":
        return (
            "Hold",
            "RSI is oversold, but trend confirmation is not strong enough for a clean buy signal.",
        )

    return (
        "Hold",
        "Signals are mixed, so the risk/reward profile does not strongly favor buying or selling right now.",
    )


def analyze_prices(
    ticker: str,
    frame: pd.DataFrame,
    currency: str = "USD",
    sma_short_window: int = 20,
    sma_long_window: int = 50,
    ema_window: int = 20,
    rsi_period: int = 14,
) -> TechnicalSnapshot:
    """Calculate indicators, trend, volatility, and recommendation."""

    if min(sma_short_window, sma_long_window, ema_window, rsi_period) <= 1:
        raise ValueError("Indicator windows must be greater than 1.")

    normalized = normalize_ohlcv_frame(frame)
    close = normalized["Close"].astype(float)

    sma_short = simple_moving_average(close, sma_short_window)
    sma_long = simple_moving_average(close, sma_long_window)
    ema = exponential_moving_average(close, ema_window)
    rsi = relative_strength_index(close, rsi_period)
    daily_vol, annualized_vol = calculate_volatility(close)

    current_price = float(close.iloc[-1])
    sma_20_value = round_float(sma_short.iloc[-1])
    sma_50_value = round_float(sma_long.iloc[-1])
    ema_20_value = round_float(ema.iloc[-1])
    rsi_14_value = round_float(rsi.iloc[-1])

    trend = detect_trend(close, sma_20_value, sma_50_value)
    momentum = classify_momentum(rsi_14_value)
    recommendation, reason = choose_recommendation(
        trend=trend,
        momentum=momentum,
        annualized_volatility=annualized_vol,
        current_price=current_price,
        sma_20=sma_20_value,
        sma_50=sma_50_value,
    )

    return TechnicalSnapshot(
        ticker=ticker.upper(),
        latest_date=str(normalized["Date"].iloc[-1]),
        current_price=current_price,
        currency=currency,
        sma_20=sma_20_value,
        sma_50=sma_50_value,
        ema_20=ema_20_value,
        rsi_14=rsi_14_value,
        daily_volatility=daily_vol,
        annualized_volatility=annualized_vol,
        trend=trend,
        momentum=momentum,
        recommendation=recommendation,
        recommendation_reason=reason,
    )


def summarize_price_history(frame: pd.DataFrame, lookback_rows: int = 5) -> list[dict[str, Any]]:
    """Return a compact recent OHLCV sample."""

    normalized = normalize_ohlcv_frame(frame)
    columns = [column for column in ["Date", "Open", "High", "Low", "Close", "Volume"] if column in normalized]
    sample = normalized[columns].tail(lookback_rows).copy()

    for column in ["Open", "High", "Low", "Close"]:
        if column in sample:
            sample[column] = sample[column].map(lambda value: round_float(value))
    if "Volume" in sample:
        sample["Volume"] = sample["Volume"].fillna(0).astype(int)

    return sample.to_dict(orient="records")


def build_report(
    snapshot: TechnicalSnapshot,
    company_name: str | None = None,
    sector: str | None = None,
    alpha_vantage_note: str | None = None,
) -> str:
    """Build the final financial report text."""

    identity = f"{company_name} ({snapshot.ticker})" if company_name else snapshot.ticker
    sector_line = f"\nSector: {sector}" if sector else ""
    alpha_line = f"\nData Note: {alpha_vantage_note}" if alpha_vantage_note else ""
    volatility = f"{snapshot.annualized_volatility:.2%}" if snapshot.annualized_volatility is not None else "Unavailable"

    return (
        f"Financial Report for {identity}\n\n"
        f"* Current Price: {format_money(snapshot.current_price, snapshot.currency)} "
        f"(latest close: {snapshot.latest_date})\n"
        f"* Trend: {snapshot.trend}\n"
        f"* RSI: {format_number(snapshot.rsi_14)} ({snapshot.momentum})\n"
        f"* Moving Averages: SMA 20: {format_money(snapshot.sma_20, snapshot.currency)}, "
        f"SMA 50: {format_money(snapshot.sma_50, snapshot.currency)}, "
        f"EMA 20: {format_money(snapshot.ema_20, snapshot.currency)}\n"
        f"* Volatility: {volatility} annualized{sector_line}{alpha_line}\n\n"
        f"Analysis: {analysis_sentence(snapshot)}\n\n"
        f"Recommendation: {snapshot.recommendation} - {snapshot.recommendation_reason}\n\n"
        "Risk Note: This is an analytical signal summary, not personalized financial advice. "
        "Validate with fundamentals, news, position sizing, and your own risk policy before trading."
    )


def analysis_sentence(snapshot: TechnicalSnapshot) -> str:
    """Generate a concise explanation of the current setup."""

    price = format_money(snapshot.current_price, snapshot.currency)
    sma_20 = format_money(snapshot.sma_20, snapshot.currency)
    sma_50 = format_money(snapshot.sma_50, snapshot.currency)
    rsi = format_number(snapshot.rsi_14)

    if snapshot.trend == "Bullish":
        return (
            f"{snapshot.ticker} is trading at {price}, with price action above or improving against "
            f"the 20-day and 50-day moving averages ({sma_20} / {sma_50}). "
            f"RSI at {rsi} suggests {snapshot.momentum.lower()} momentum."
        )
    if snapshot.trend == "Bearish":
        return (
            f"{snapshot.ticker} is trading at {price}, with price action below key moving averages "
            f"({sma_20} / {sma_50}). RSI at {rsi} points to {snapshot.momentum.lower()} momentum."
        )
    return (
        f"{snapshot.ticker} is trading at {price} with mixed signals around the 20-day and 50-day "
        f"moving averages ({sma_20} / {sma_50}). RSI at {rsi} indicates {snapshot.momentum.lower()} momentum."
    )


def format_money(value: float | int | None, currency: str = "USD") -> str:
    """Format a currency value."""

    rounded = round_float(value)
    if rounded is None:
        return "Unavailable"
    return f"{currency} {rounded:,.2f}"


def format_number(value: float | int | None) -> str:
    """Format a numeric metric."""

    rounded = round_float(value)
    if rounded is None:
        return "Unavailable"
    return f"{rounded:.2f}"
