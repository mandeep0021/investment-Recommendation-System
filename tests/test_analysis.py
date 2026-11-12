import unittest
from datetime import date
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd

from analysis import (
    MarketDataError,
    backtest_buy_and_hold,
    calculate_return_metrics,
    fetch_market_history,
    get_market_screen,
    parse_tickers,
)


class AnalysisTests(unittest.TestCase):
    def test_ticker_parser_normalizes_deduplicates_and_limits(self):
        self.assertEqual(parse_tickers("aapl, MSFT AAPL; infy.ns"), ["AAPL", "MSFT", "INFY.NS"])
        with self.assertRaisesRegex(ValueError, "at least one"):
            parse_tickers(" , ")
        with self.assertRaisesRegex(ValueError, "no more than 2"):
            parse_tickers("AAPL, MSFT, NVDA", max_tickers=2)
        with self.assertRaisesRegex(ValueError, "Invalid ticker"):
            parse_tickers("AAPL/../private")

    @patch("analysis.requests.get")
    def test_fetch_market_history_parses_adjusted_daily_prices(self, get):
        get.return_value = Mock(
            status_code=200,
            json=lambda: {
                "chart": {
                    "error": None,
                    "result": [
                        {
                            "meta": {
                                "symbol": "AAPL",
                                "longName": "Apple Inc.",
                                "currency": "USD",
                                "exchangeName": "NMS",
                                "exchangeTimezoneName": "America/New_York",
                            },
                            "timestamp": [1735765200, 1735851600, 1735938000],
                            "indicators": {
                                "quote": [{"close": [100, 103, 106], "volume": [1000, 1100, 1200]}],
                                "adjclose": [{"adjclose": [99, 102, 105]}],
                            },
                        }
                    ],
                }
            },
        )
        get.return_value.raise_for_status.return_value = None

        history, metadata = fetch_market_history(
            "AAPL", date(2025, 1, 1), date(2025, 1, 3)
        )

        self.assertEqual(history["adjusted_close"].tolist(), [99, 102, 105])
        self.assertEqual(metadata["currency"], "USD")
        self.assertEqual(metadata["name"], "Apple Inc.")
        get.assert_called_once()

    @patch("analysis.requests.get")
    def test_fetch_market_history_reports_ticker_errors(self, get):
        get.return_value = Mock(
            json=lambda: {
                "chart": {
                    "error": {"description": "Not found"},
                    "result": None,
                }
            }
        )
        get.return_value.raise_for_status.return_value = None

        with self.assertRaisesRegex(MarketDataError, "No market data for INVALID"):
            fetch_market_history("INVALID", date(2025, 1, 1), date(2025, 1, 3))

    def test_market_metrics_and_screen_are_calculated_from_history(self):
        dates = pd.date_range("2024-01-01", periods=253, freq="B")
        prices = pd.Series(np.linspace(100, 120, len(dates)), index=dates)
        metrics = calculate_return_metrics(prices)
        self.assertAlmostEqual(metrics["period_return_pct"], 20.0)
        self.assertEqual(metrics["observations"], 253)
        self.assertGreater(metrics["annualized_volatility_pct"], 0)
        self.assertEqual(get_market_screen(12, 20, 120, 115), "Buy")
        self.assertEqual(get_market_screen(-10, 30, 90, 100), "Sell")
        self.assertEqual(get_market_screen(5, 60, 110, 100), "Hold")

    def test_market_metrics_reject_insufficient_observations(self):
        prices = pd.Series(
            [100, 101],
            index=pd.date_range("2025-01-01", periods=2, freq="B"),
        )
        with self.assertRaisesRegex(ValueError, "At least three"):
            calculate_return_metrics(prices)

    def test_buy_and_hold_backtest_uses_fixed_shares_and_normalized_weights(self):
        dates = pd.date_range("2024-01-01", periods=4, freq="B")
        prices = pd.DataFrame(
            {"A": [100, 110, 120, 120], "B": [100, 95, 90, 90]},
            index=dates,
        )
        values, metrics, weights = backtest_buy_and_hold(prices, {"A": 75, "B": 25}, 10000)
        self.assertAlmostEqual(values.iloc[-1], 11250)
        self.assertAlmostEqual(metrics["period_return_pct"], 12.5)
        self.assertAlmostEqual(weights["A"], 0.75)
        self.assertAlmostEqual(sum(weights.values()), 1)

    def test_backtest_rejects_non_positive_capital_and_unaligned_prices(self):
        prices = pd.DataFrame({"A": [100, 110]}, index=pd.date_range("2024-01-01", periods=2))
        with self.assertRaisesRegex(ValueError, "positive finite"):
            backtest_buy_and_hold(prices, {"A": 100}, 0)
        unaligned = pd.DataFrame(
            {"A": [100, np.nan], "B": [np.nan, 200]},
            index=pd.date_range("2024-01-01", periods=2),
        )
        with self.assertRaisesRegex(ValueError, "shared valid trading dates"):
            backtest_buy_and_hold(unaligned, {"A": 50, "B": 50}, 1000)

    def test_zero_weight_assets_do_not_restrict_backtest_dates(self):
        dates = pd.date_range("2024-01-01", periods=3, freq="B")
        prices = pd.DataFrame(
            {"A": [100, 105, 110], "B": [np.nan, np.nan, 200]},
            index=dates,
        )
        values, _, weights = backtest_buy_and_hold(
            prices, {"A": 100, "B": 0}, 1000
        )
        self.assertAlmostEqual(values.iloc[-1], 1100)
        self.assertEqual(weights, {"A": 1.0, "B": 0.0})


if __name__ == "__main__":
    unittest.main()
