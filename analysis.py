"""Data providers and decision-support calculations for the dashboard."""

import re
from datetime import date, datetime, time, timedelta, timezone
from typing import Mapping

import numpy as np
import pandas as pd
import requests


TICKER_PATTERN = re.compile(r"^[A-Za-z0-9.^=_-]{1,32}$")
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"


class MarketDataError(ValueError):
    """Raised when the public market-data provider cannot return usable data."""


def parse_tickers(value: str, max_tickers: int = 8) -> list[str]:
    """Parse and validate a comma- or whitespace-separated ticker list."""
    tickers = []
    seen = set()
    for token in re.split(r"[\s,;]+", value.strip()):
        symbol = token.upper()
        if not symbol:
            continue
        if not TICKER_PATTERN.fullmatch(symbol):
            raise ValueError(f"Invalid ticker '{token}'. Use letters, numbers, '.', '^', '=', '_', or '-'.")
        if symbol not in seen:
            tickers.append(symbol)
            seen.add(symbol)
    if not tickers:
        raise ValueError("Enter at least one ticker symbol.")
    if len(tickers) > max_tickers:
        raise ValueError(f"Enter no more than {max_tickers} unique tickers.")
    return tickers


def fetch_market_history(
    symbol: str, start_date: date, end_date: date, timeout: float = 15
) -> tuple[pd.DataFrame, dict[str, str]]:
    """Fetch daily adjusted close prices from Yahoo Finance's public chart endpoint."""
    if not TICKER_PATTERN.fullmatch(symbol):
        raise ValueError(f"Invalid ticker symbol: {symbol}")
    if start_date > end_date:
        raise ValueError("Start date must be on or before end date.")

    start = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
    end_exclusive = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=timezone.utc)
    try:
        response = requests.get(
            YAHOO_CHART_URL.format(symbol=symbol),
            params={
                "period1": int(start.timestamp()),
                "period2": int(end_exclusive.timestamp()),
                "interval": "1d",
                "events": "div,splits",
            },
            headers={"User-Agent": "Mozilla/5.0 (compatible; InvestmentResearchDashboard/1.0)"},
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as error:
        raise MarketDataError(
            f"Could not retrieve {symbol}. Check your internet connection and try again; "
            "Yahoo Finance may also be temporarily unavailable or rate-limiting requests."
        ) from error
    except ValueError as error:
        raise MarketDataError(f"The market-data response for {symbol} was not valid JSON.") from error

    if not isinstance(payload, dict):
        raise MarketDataError(f"The market-data response for {symbol} was not a JSON object.")
    chart = payload.get("chart", {})
    if chart.get("error"):
        description = chart["error"].get("description") or "provider rejected the ticker or request"
        raise MarketDataError(f"No market data for {symbol}: {description}.")
    results = chart.get("result") or []
    if not results:
        raise MarketDataError(
            f"No daily history was returned for {symbol} in the selected date range. "
            "Check the ticker format and available history."
        )

    result = results[0]
    metadata = result.get("meta") or {}
    timestamps = result.get("timestamp") or []
    indicators = result.get("indicators") or {}
    quote_list = indicators.get("quote") or []
    if not timestamps or not quote_list:
        raise MarketDataError(f"The market-data response for {symbol} did not contain daily prices.")

    quote = quote_list[0]
    closes = quote.get("close") or []
    volumes = quote.get("volume") or []
    adjusted_groups = indicators.get("adjclose") or []
    adjusted_closes = adjusted_groups[0].get("adjclose") if adjusted_groups else None
    if adjusted_closes is None:
        adjusted_closes = closes
    if len(timestamps) != len(closes) or len(timestamps) != len(adjusted_closes):
        raise MarketDataError(f"The market-data response for {symbol} had inconsistent price arrays.")
    if not volumes:
        volumes = [None] * len(timestamps)
    if len(timestamps) != len(volumes):
        raise MarketDataError(f"The market-data response for {symbol} had inconsistent volume values.")

    exchange_timezone = metadata.get("exchangeTimezoneName") or "UTC"
    try:
        dates = pd.to_datetime(timestamps, unit="s", utc=True).tz_convert(exchange_timezone).tz_localize(None)
    except (TypeError, ValueError, KeyError) as error:
        raise MarketDataError(f"The provider returned an unsupported exchange timezone for {symbol}.") from error

    history = pd.DataFrame(
        {
            "adjusted_close": adjusted_closes,
            "close": closes,
            "volume": volumes,
        },
        index=pd.DatetimeIndex(dates, name="date"),
    )
    for column in ("adjusted_close", "close", "volume"):
        history[column] = pd.to_numeric(history[column], errors="coerce")
    history = history.replace([np.inf, -np.inf], np.nan).dropna(subset=["adjusted_close", "close"])
    history = history.loc[
        (history.index.date >= start_date) & (history.index.date <= end_date)
    ]
    history = history[(history["adjusted_close"] > 0) & (history["close"] > 0)]
    if len(history) < 3:
        raise MarketDataError(f"Fewer than three usable daily prices were returned for {symbol}.")

    asset_metadata = {
        "symbol": str(metadata.get("symbol") or symbol),
        "name": str(metadata.get("longName") or metadata.get("shortName") or symbol),
        "currency": str(metadata.get("currency") or "Unknown"),
        "exchange": str(metadata.get("fullExchangeName") or metadata.get("exchangeName") or "Unknown"),
        "timezone": exchange_timezone,
    }
    return history, asset_metadata


def calculate_return_metrics(prices: pd.Series) -> dict[str, float | int | str]:
    """Calculate historical performance statistics from a daily positive price series."""
    series = pd.to_numeric(prices, errors="coerce").dropna()
    series = series[np.isfinite(series) & (series > 0)]
    if len(series) < 3:
        raise ValueError("At least three positive daily prices are required for performance analysis.")
    daily_returns = series.pct_change().dropna()
    period_return = (float(series.iloc[-1]) / float(series.iloc[0]) - 1) * 100
    elapsed_days = max((series.index[-1] - series.index[0]).days, 1)
    years = elapsed_days / 365.25
    annualized_return = ((float(series.iloc[-1]) / float(series.iloc[0])) ** (1 / years) - 1) * 100
    daily_std = float(daily_returns.std(ddof=1))
    annualized_volatility = float(daily_std * np.sqrt(252) * 100)
    sharpe_ratio = (
        float(daily_returns.mean() / daily_std * np.sqrt(252))
        if np.isfinite(daily_std) and daily_std > 0
        else 0.0
    )
    drawdown = series / series.cummax() - 1
    return {
        "period_return_pct": period_return,
        "annualized_return_pct": annualized_return,
        "annualized_volatility_pct": annualized_volatility,
        "sharpe_ratio": sharpe_ratio,
        "max_drawdown_pct": float(drawdown.min() * 100),
        "observations": int(len(series)),
        "latest_price": float(series.iloc[-1]),
    }


def get_market_screen(
    annualized_return_pct: float,
    annualized_volatility_pct: float,
    latest_price: float,
    trend_average: float,
) -> str:
    """Return a transparent, unpersonalized historical-momentum screening label."""
    if annualized_return_pct >= 8 and annualized_volatility_pct <= 45 and latest_price >= trend_average:
        return "Buy"
    if annualized_return_pct < 0 and latest_price < trend_average:
        return "Sell"
    return "Hold"


def backtest_buy_and_hold(
    adjusted_prices: pd.DataFrame,
    weights: Mapping[str, float],
    initial_investment: float,
) -> tuple[pd.Series, dict[str, float | int | str], dict[str, float]]:
    """Simulate static-share buy-and-hold positions with normalized starting allocations."""
    if not np.isfinite(initial_investment) or initial_investment <= 0:
        raise ValueError("Initial investment must be a positive finite amount.")
    if adjusted_prices.empty or not weights:
        raise ValueError("Select at least one asset with historical price data.")
    if set(weights).difference(adjusted_prices.columns):
        raise ValueError("Portfolio weights contain assets without price data.")
    if any(not np.isfinite(float(weight)) or float(weight) < 0 for weight in weights.values()):
        raise ValueError("Portfolio allocations must be finite and non-negative.")
    total_weight = sum(float(weight) for weight in weights.values())
    if total_weight <= 0:
        raise ValueError("Portfolio allocations must add up to more than zero.")

    normalized_weights = {symbol: float(weight) / total_weight for symbol, weight in weights.items()}
    active_weights = {
        symbol: weight for symbol, weight in normalized_weights.items() if weight > 0
    }
    aligned_prices = adjusted_prices[list(active_weights)].apply(pd.to_numeric, errors="coerce")
    aligned_prices = aligned_prices.replace([np.inf, -np.inf], np.nan).dropna(how="any")
    aligned_prices = aligned_prices[(aligned_prices > 0).all(axis=1)]
    if len(aligned_prices) < 2:
        raise ValueError("Selected assets need at least two shared valid trading dates for a backtest.")

    indexed_prices = aligned_prices.divide(aligned_prices.iloc[0], axis="columns")
    value = sum(indexed_prices[symbol] * weight for symbol, weight in active_weights.items())
    portfolio_value = value * float(initial_investment)
    portfolio_value.name = "Portfolio value"
    metrics = calculate_return_metrics(portfolio_value)
    return portfolio_value, metrics, normalized_weights


