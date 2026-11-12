# Investment Recommendation System

A local research dashboard for analyzing historical market data retrieved from Yahoo Finance. It compares tickers, calculates historical risk and return measures, applies a transparent screen, and simulates same-currency portfolios. No synthetic price history or pre-filled market metrics are included.

> Historical performance is not a forecast or personalized investment advice. The app does not execute trades.

## Run locally

Use Python 3.10 or later. Open a terminal in this folder:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open the local URL printed by Streamlit, usually `http://localhost:8501`.
The app is configured to bind to `127.0.0.1` and is intended for this computer only. Do not expose it on a LAN, through port forwarding, or through a tunnel.

On Windows, double-click [`run_dashboard.bat`](run_dashboard.bat). Keep its console open while using the app. Closing it stops the local server.

## Use the dashboard

1. Enter up to eight Yahoo Finance ticker symbols, such as `AAPL`, `MSFT`, `INFY.NS`, or `TCS.NS`.
2. Optionally enter a benchmark such as `^GSPC`, `^NSEI`, or `SPY`.
3. Choose a history period, then select **Fetch market history**.
4. Review adjusted-price returns, volatility, Sharpe ratio, drawdown, and the historical screen.
5. In **Portfolio backtest**, select assets quoted in one currency, set allocations, and review the simulation.
6. Download the market report, adjusted-price CSV, portfolio backtest CSV, or portfolio summary TXT.

Successful requests are cached in memory for 15 minutes. A failed symbol is reported; synthetic data is not substituted. The provider is unofficial and may delay, change, rate-limit, or block requests.

The interface wraps its tabs and input columns for narrow screens. The sidebar starts collapsed so the main controls remain visible on mobile; use its menu button to open the market-data notes. The hero banner and primary action use restrained motion, and metric/chart reveals respect reduced-motion preferences. The app has a browser title, description, custom favicon, clickable brand header, and dynamically dated footer. Streamlit usage statistics are disabled in the local project configuration.

## Privacy and terms

The **Privacy policy** and **Terms and conditions** tabs display [privacy_policy.md](privacy_policy.md) and [terms_and_conditions.md](terms_and_conditions.md). These are plain-language project notices, not legal advice. They require review before any public release.

## Calculations and limitations

- Adjusted closes are used when supplied by the provider.
- Annualized return compounds the first-to-last price change over the observed calendar period.
- Annualized volatility uses daily return sample standard deviation multiplied by the square root of 252.
- Sharpe ratio assumes a 0% risk-free rate.
- Maximum drawdown is measured against the running adjusted-price high.
- Buy/Hold/Sell labels use the documented historical-momentum thresholds. They do not predict future results.
- Portfolio weights are normalized across the selected assets. The backtest is a total-return proxy without periodic rebalancing, fees, taxes, or FX conversion.

## Verify and regenerate

```powershell
python -m unittest discover -s tests -v
python -m compileall app.py analysis.py generate_deliverables.py tests
python generate_deliverables.py
```

## Project files

- `app.py` - Streamlit application
- `analysis.py` - market data client, validation, analytics, and backtest
- `.streamlit/config.toml` - local theme and telemetry settings
- `assets/favicon.svg` and `assets/favicon.png` - custom browser icon
- `privacy_policy.md` and `terms_and_conditions.md` - policy pages displayed in the app
- `tests/test_analysis.py` - offline tests; no network calls required
- `project_report.md` and `project_report.pdf` - capstone report
- `presentation_outline.md` and `presentation.pptx` - presentation deliverables
- `deployment.md` - pre-launch checklist
- `run_dashboard.bat` - Windows launcher

The app is local only. Do not deploy or publish it until a custom domain is connected and the policy and hosting details have been reviewed. No domain has been provided or connected.
