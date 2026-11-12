import base64
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from analysis import (
    MarketDataError,
    backtest_buy_and_hold,
    calculate_return_metrics,
    fetch_market_history,
    get_market_screen,
    parse_tickers,
)

PROJECT_DIR = Path(__file__).resolve().parent
FAVICON_PATH = PROJECT_DIR / "assets" / "favicon.png"
LOGO_SVG_PATH = PROJECT_DIR / "assets" / "favicon.svg"
PRIVACY_POLICY_PATH = PROJECT_DIR / "privacy_policy.md"
TERMS_PATH = PROJECT_DIR / "terms_and_conditions.md"
LOOKBACK_DAYS = {"1 month": 31, "3 months": 93, "6 months": 186, "1 year": 366, "3 years": 1096, "5 years": 1827}


@st.cache_data(ttl=900, show_spinner=False)
def get_cached_history(symbol: str, start_date: str, end_date: str):
    return fetch_market_history(symbol, date.fromisoformat(start_date), date.fromisoformat(end_date))


def build_market_summary(histories, metadata):
    rows = []
    for symbol, history in histories.items():
        metrics = calculate_return_metrics(history["adjusted_close"])
        trend_window = min(50, len(history))
        trend_average = float(history["adjusted_close"].tail(trend_window).mean())
        rows.append(
            {
                "Ticker": symbol,
                "Name": metadata[symbol]["name"],
                "Exchange": metadata[symbol]["exchange"],
                "Currency": metadata[symbol]["currency"],
                "Latest adjusted close": metrics["latest_price"],
                "Period return (%)": metrics["period_return_pct"],
                "Annualized return (%)": metrics["annualized_return_pct"],
                "Annualized volatility (%)": metrics["annualized_volatility_pct"],
                "Sharpe ratio (0% risk-free)": metrics["sharpe_ratio"],
                "Maximum drawdown (%)": metrics["max_drawdown_pct"],
                "Screen": get_market_screen(
                    metrics["annualized_return_pct"],
                    metrics["annualized_volatility_pct"],
                    metrics["latest_price"],
                    trend_average,
                ),
                "Latest date": history.index[-1].date().isoformat(),
            }
        )
    return pd.DataFrame(rows)


def build_report(summary, benchmark, lookback_label, start_date, end_date):
    lines = [
        "Investment Recommendation System - Historical Market Analysis",
        "=" * 68,
        f"Data source: Yahoo Finance public chart endpoint (historical daily data)",
        f"Requested period: {lookback_label} ({start_date} through {end_date})",
        f"Generated: {date.today().isoformat()}",
        "",
        "Historical results describe the requested period; they do not predict future results.",
        "The technical screen is a transparent educational heuristic, not financial advice.",
        "Prices are adjusted closes. Sharpe ratio assumes a 0% risk-free rate and uses daily returns.",
        "",
        f"Benchmark: {benchmark or 'Not selected'}",
        "",
    ]
    for row in summary.to_dict("records"):
        lines.extend(
            [
                f"{row['Ticker']}: {row['Name']} ({row['Exchange']}, {row['Currency']})",
                f"  Latest adjusted close: {row['Latest adjusted close']:.4f} {row['Currency']}",
                f"  Latest available date: {row['Latest date']}",
                f"  Period return: {row['Period return (%)']:.2f}%",
                f"  Annualized return: {row['Annualized return (%)']:.2f}%",
                f"  Annualized volatility: {row['Annualized volatility (%)']:.2f}%",
                f"  Sharpe ratio (0% risk-free): {row['Sharpe ratio (0% risk-free)']:.2f}",
                f"  Maximum drawdown: {row['Maximum drawdown (%)']:.2f}%",
                f"  Heuristic screen: {row['Screen']}",
                "",
            ]
        )
    return "\n".join(lines)


st.set_page_config(
    page_title="Investment Recommendation System | Historical Market Research",
    page_icon=str(FAVICON_PATH),
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        "About": "Historical market research for education. Results are not financial advice."
    },
)
st.html(
    """
    <script>
      (function () {
        const descriptionText =
          "Explore historical market performance, risk metrics, transparent screening rules, and portfolio backtests.";
        let descriptionTag = document.head.querySelector('meta[name="description"]');
        if (!descriptionTag) {
          descriptionTag = document.createElement("meta");
          descriptionTag.name = "description";
          document.head.appendChild(descriptionTag);
        }
        descriptionTag.content = descriptionText;
      })();
    </script>
    """,
    unsafe_allow_javascript=True,
)
logo_data = base64.b64encode(LOGO_SVG_PATH.read_bytes()).decode("ascii")
st.markdown(
    f"""
    <section class="hero-banner" aria-labelledby="app-home">
      <h1 id="app-home" class="brand-heading">
        <a class="brand-link" href="#app-home" aria-label="Investment Recommendation System home">
          <img src="data:image/svg+xml;base64,{logo_data}" alt="" width="42" height="42">
          <span>Investment Recommendation System</span>
        </a>
      </h1>
      <p class="hero-description">Historical prices, risk measures, and portfolio backtests.</p>
    </section>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    """
    <style>
      .hero-banner {
        margin: 0 0 1rem;
        padding: 1.25rem 1.5rem;
        background: #F2F4F5;
        border: 1px solid rgba(36,49,58,.14);
        border-radius: 4px;
        animation: hero-enter 300ms ease-out both;
      }
      .brand-heading { margin: 0; font-size: 2.45rem; line-height: 1.15; }
      .brand-link { display: inline-flex; align-items: center; gap: .75rem; color: inherit; text-decoration: none; }
      .brand-link:hover { color: inherit; text-decoration: none; }
      .hero-description { margin: .45rem 0 0 3.375rem; color: #495860; font-size: .95rem; }
      .app-footer { margin-top: 2rem; padding: 1rem 0 .5rem; border-top: 1px solid rgba(128,128,128,.3); font-size: .85rem; opacity: .8; }
      .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] { max-width: 100%; overflow-x: hidden; }
      @keyframes hero-enter {
        from { opacity: 0; transform: translateY(6px); }
        to { opacity: 1; transform: translateY(0); }
      }
      @keyframes result-reveal {
        from { opacity: 0; transform: translateY(4px); }
        to { opacity: 1; transform: translateY(0); }
      }
      [data-testid="stMetric"], [data-testid="stPlotlyChart"] {
        animation: result-reveal 220ms ease-out both;
      }
      button[data-testid*="stBaseButton-primary"] {
        transition: transform 140ms ease, background-color 140ms ease;
      }
      button[data-testid*="stBaseButton-primary"]:hover { transform: translateY(-1px); }
      button[data-testid*="stBaseButton-primary"]:active { transform: translateY(0); }
      @media (prefers-reduced-motion: reduce) {
        .hero-banner, [data-testid="stMetric"], [data-testid="stPlotlyChart"] { animation: none; }
        button[data-testid*="stBaseButton-primary"] { transition: none; }
      }
      button[data-testid^="stBaseButton"] { border-radius: 4px !important; }
      input, [data-baseweb="select"] > div { border-radius: 4px !important; }
      @media (max-width: 900px) {
        div[role="tablist"] { flex-wrap: wrap !important; overflow: visible !important; white-space: normal !important; gap: .2rem; }
        button[role="tab"] { flex: 1 1 45% !important; width: auto !important; min-width: 0 !important; white-space: normal !important; min-height: 2.75rem; }
      }
      @media (max-width: 760px) {
        .block-container { padding: 1rem .85rem 2rem; }
        .hero-banner { padding: 1rem; }
        .brand-heading { font-size: 1.65rem; }
        .brand-link { gap: .5rem; }
        .brand-link img { width: 34px; height: 34px; }
        .hero-description { margin-left: 2.625rem; }
        .stHorizontalBlock { flex-wrap: wrap !important; gap: .65rem; }
        .stHorizontalBlock > div[data-testid="column"] { flex: 1 1 100% !important; min-width: min(100%, 16rem) !important; }
        [data-testid="stPlotlyChart"], [data-testid="stDataFrame"], [data-testid="stTable"] { max-width: 100%; }
      }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Market data")
    st.caption("Yahoo Finance historical data. Quotes may be delayed; availability and coverage depend on the provider.")
    st.info("Ticker examples: AAPL, MSFT, INFY.NS, TCS.NS, HDFCBANK.NS, ^NSEI")
    st.caption("This tool is for educational research, not personalized investment advice.")

with st.form("market_data_form"):
    st.subheader("Choose your research universe")
    input_col, benchmark_col, period_col = st.columns([3, 1, 1])
    tickers_input = input_col.text_input(
        "Tickers (comma-separated, up to 8)",
        value="AAPL, MSFT, GOOGL, NVDA",
        help="Use Yahoo Finance ticker format. Add .NS for NSE-listed symbols, for example INFY.NS.",
    )
    benchmark_input = benchmark_col.text_input(
        "Benchmark (optional)",
        value="^GSPC",
        help="Examples: ^GSPC (S&P 500), ^NSEI (Nifty 50), SPY.",
    )
    lookback_label = period_col.selectbox("History", list(LOOKBACK_DAYS), index=3)
    fetch_submitted = st.form_submit_button("Fetch market history", type="primary")

if fetch_submitted:
    for key in (
        "market_histories",
        "market_metadata",
        "market_errors",
        "market_assets",
        "market_benchmark",
        "market_period",
        "market_start_date",
        "market_end_date",
        "market_success",
    ):
        st.session_state.pop(key, None)
    try:
        requested_symbols = parse_tickers(tickers_input)
        benchmark_symbols = parse_tickers(benchmark_input, max_tickers=1) if benchmark_input.strip() else []
        if benchmark_symbols and benchmark_symbols[0] in requested_symbols:
            raise ValueError("Choose a benchmark that is different from the assets being analyzed.")
    except ValueError as error:
        st.error(str(error))
    else:
        end_date = date.today()
        start_date = end_date - timedelta(days=LOOKBACK_DAYS[lookback_label])
        symbols_to_fetch = requested_symbols + benchmark_symbols
        fetched_histories = {}
        fetched_metadata = {}
        fetch_errors = {}
        progress = st.progress(0, text="Requesting daily history...")
        for index, symbol in enumerate(symbols_to_fetch, start=1):
            try:
                history, asset_metadata = get_cached_history(
                    symbol, start_date.isoformat(), end_date.isoformat()
                )
                fetched_histories[symbol] = history
                fetched_metadata[symbol] = asset_metadata
            except MarketDataError as error:
                fetch_errors[symbol] = str(error)
            progress.progress(index / len(symbols_to_fetch), text=f"Retrieved {symbol} ({index}/{len(symbols_to_fetch)})")
        progress.empty()

        st.session_state["market_histories"] = fetched_histories
        st.session_state["market_metadata"] = fetched_metadata
        st.session_state["market_errors"] = fetch_errors
        st.session_state["market_assets"] = requested_symbols
        st.session_state["market_benchmark"] = benchmark_symbols[0] if benchmark_symbols else ""
        st.session_state["market_period"] = lookback_label
        st.session_state["market_start_date"] = start_date.isoformat()
        st.session_state["market_end_date"] = end_date.isoformat()
        loaded_asset_count = sum(symbol in fetched_histories for symbol in requested_symbols)
        if loaded_asset_count:
            st.session_state["market_success"] = (
                f"Loaded market history for {loaded_asset_count} of "
                f"{len(requested_symbols)} requested asset(s)."
            )
        else:
            st.session_state["market_success"] = ""

histories = st.session_state.get("market_histories", {})
metadata = st.session_state.get("market_metadata", {})
fetch_errors = st.session_state.get("market_errors", {})
asset_symbols = [
    symbol for symbol in st.session_state.get("market_assets", []) if symbol in histories
]
benchmark = st.session_state.get("market_benchmark", "")
lookback_label = st.session_state.get("market_period", lookback_label)
start_date_text = st.session_state.get("market_start_date", "")
end_date_text = st.session_state.get("market_end_date", "")

for symbol, message in fetch_errors.items():
    st.error(f"{symbol}: {message}")

if st.session_state.get("market_success"):
    st.success(st.session_state["market_success"])
elif fetch_errors and not asset_symbols:
    st.error("No requested asset history could be loaded. Review the ticker errors above and try again.")

if not asset_symbols:
    st.info("Enter tickers and select **Fetch market history** to load historical market prices.")

live_tab, portfolio_tab, methodology_tab, privacy_tab, terms_tab = st.tabs(
    ["Market analysis", "Portfolio backtest", "Methodology", "Privacy policy", "Terms and conditions"]
)

summary = pd.DataFrame()
with live_tab:
    st.subheader("Historical asset comparison")
    if asset_symbols:
        asset_histories = {symbol: histories[symbol] for symbol in asset_symbols}
        asset_metadata = {symbol: metadata[symbol] for symbol in asset_symbols}
        summary = build_market_summary(asset_histories, asset_metadata)
        currency_list = sorted(summary["Currency"].unique().tolist())
        if len(currency_list) > 1:
            st.warning(
                "Selected assets use different currencies. Returns are shown in each asset's local currency; "
                "no foreign-exchange conversion is applied."
            )
        st.dataframe(
            summary.style.format(
                {
                    "Latest adjusted close": "{:,.2f}",
                    "Period return (%)": "{:+.2f}",
                    "Annualized return (%)": "{:+.2f}",
                    "Annualized volatility (%)": "{:.2f}",
                    "Sharpe ratio (0% risk-free)": "{:.2f}",
                    "Maximum drawdown (%)": "{:.2f}",
                }
            ),
            width="stretch",
            hide_index=True,
        )

        chart_symbols = asset_symbols.copy()
        if benchmark and benchmark in histories:
            chart_symbols.append(benchmark)
        normalized_series = []
        for symbol in chart_symbols:
            closes = histories[symbol]["adjusted_close"].dropna()
            normalized = closes / closes.iloc[0] * 100
            normalized_series.append(normalized.rename(symbol))
        indexed_performance = pd.concat(normalized_series, axis=1)
        performance_figure = px.line(
            indexed_performance,
            title="Indexed adjusted-price performance (first available close = 100)",
            labels={"value": "Indexed value", "index": "Date", "variable": "Ticker"},
            template="plotly_white",
        )
        st.plotly_chart(performance_figure, width="stretch")

        selected_symbol = st.selectbox("Inspect an asset", asset_symbols)
        selected_history = histories[selected_symbol]
        selected_close = selected_history["adjusted_close"].dropna()
        selected_window = min(50, len(selected_close))
        moving_average = selected_close.rolling(selected_window, min_periods=selected_window).mean()
        asset_figure = px.line(
            pd.DataFrame(
                {
                    "Adjusted close": selected_close,
                    f"{selected_window}-session moving average": moving_average,
                }
            ),
            title=f"{metadata[selected_symbol]['name']}: adjusted daily price",
            template="plotly_white",
        )
        asset_figure.update_layout(yaxis_title=f"Adjusted close ({metadata[selected_symbol]['currency']})")
        st.plotly_chart(asset_figure, width="stretch")
        st.caption(
            "The moving average uses up to 50 available trading sessions. Historical returns and this simple "
            "screen are descriptive only; they do not forecast future performance."
        )

        report = build_report(
            summary,
            benchmark if benchmark in histories else "",
            st.session_state.get("market_period", ""),
            start_date_text,
            end_date_text,
        )
        st.download_button(
            "Download market analysis report",
            report,
            file_name="historical_market_analysis.txt",
            mime="text/plain",
        )
        export_frames = []
        for symbol in chart_symbols:
            frame = histories[symbol][["adjusted_close"]].rename(
                columns={"adjusted_close": symbol}
            )
            export_frames.append(frame)
        price_export = pd.concat(export_frames, axis=1)
        st.download_button(
            "Download adjusted-price history (CSV)",
            price_export.to_csv(index_label="date").encode("utf-8"),
            file_name="adjusted_price_history.csv",
            mime="text/csv",
        )
    else:
        st.caption("The live analysis appears here after a successful history fetch.")

with portfolio_tab:
    st.subheader("Historical buy-and-hold total-return simulation")
    if not asset_symbols:
        st.info("Fetch market history first to enable the backtest.")
    else:
        selected_portfolio = st.multiselect(
            "Select assets for the portfolio",
            asset_symbols,
            default=asset_symbols[: min(3, len(asset_symbols))],
            max_selections=8,
        )
        if not selected_portfolio:
            st.info("Select at least one asset.")
        else:
            selected_currencies = {
                metadata[symbol]["currency"] for symbol in selected_portfolio
            }
            if len(selected_currencies) != 1 or "Unknown" in selected_currencies:
                st.error(
                    "Choose assets quoted in the same known currency. The backtest does not convert foreign exchange."
                )
            else:
                currency = next(iter(selected_currencies))
                initial_investment = st.number_input(
                    f"Starting investment ({currency})",
                    min_value=1.0,
                    value=10000.0,
                    step=1000.0,
                )
                allocation_columns = st.columns(min(len(selected_portfolio), 4))
                allocations = {}
                for index, symbol in enumerate(selected_portfolio):
                    with allocation_columns[index % len(allocation_columns)]:
                        allocations[symbol] = st.number_input(
                            f"{symbol} allocation (%)",
                            min_value=0,
                            max_value=100,
                            value=max(1, 100 // len(selected_portfolio)),
                            key=f"backtest_weight_{symbol}",
                        )
                if sum(allocations.values()) == 0:
                    st.error("Give at least one asset a positive allocation.")
                else:
                    selected_prices = pd.concat(
                        {
                            symbol: histories[symbol]["adjusted_close"]
                            for symbol in selected_portfolio
                        },
                        axis=1,
                    )
                    try:
                        portfolio_value, portfolio_metrics, normalized_weights = backtest_buy_and_hold(
                            selected_prices, allocations, initial_investment
                        )
                    except ValueError as error:
                        st.error(str(error))
                    else:
                        total_allocation = sum(allocations.values())
                        st.caption(
                            f"Entered allocations total {total_allocation}%; weights are normalized to 100%. "
                            "This is an adjusted-price total-return simulation: provider corporate-action "
                            "adjustments are reflected, and the portfolio is not periodically rebalanced."
                        )
                        st.success("Portfolio analysis is ready. You can download the values or summary below.")
                        metric_columns = st.columns(4)
                        metric_columns[0].metric(
                            "Ending value",
                            f"{currency} {portfolio_value.iloc[-1]:,.2f}",
                            f"{portfolio_metrics['period_return_pct']:+.2f}%",
                        )
                        metric_columns[1].metric(
                            "Annualized return",
                            f"{portfolio_metrics['annualized_return_pct']:+.2f}%",
                        )
                        metric_columns[2].metric(
                            "Annualized volatility",
                            f"{portfolio_metrics['annualized_volatility_pct']:.2f}%",
                        )
                        metric_columns[3].metric(
                            "Maximum drawdown",
                            f"{portfolio_metrics['max_drawdown_pct']:.2f}%",
                        )

                        portfolio_index = portfolio_value / initial_investment * 100
                        backtest_chart = pd.DataFrame(
                            {"Portfolio index (start = 100)": portfolio_index}
                        )
                        if benchmark and benchmark in histories:
                            benchmark_currency = metadata[benchmark]["currency"]
                            if benchmark_currency != currency:
                                st.warning(
                                    f"Benchmark {benchmark} is in {benchmark_currency}, while the portfolio is in "
                                    f"{currency}. The indexed benchmark comparison excludes FX effects."
                                )
                            benchmark_prices = histories[benchmark]["adjusted_close"].dropna()
                            benchmark_index = benchmark_prices / benchmark_prices.iloc[0] * 100
                            backtest_chart[benchmark] = benchmark_index.reindex(backtest_chart.index)
                        figure = px.line(
                            backtest_chart,
                            title="Backtest value indexed to 100",
                            labels={"value": "Indexed value", "index": "Date", "variable": "Series"},
                            template="plotly_white",
                        )
                        st.plotly_chart(figure, width="stretch")
                        st.dataframe(
                            pd.DataFrame(
                                [
                                    {
                                        "Ticker": symbol,
                                        "Normalized allocation (%)": weight * 100,
                                        "Currency": currency,
                                    }
                                    for symbol, weight in normalized_weights.items()
                                ]
                            ).style.format({"Normalized allocation (%)": "{:.2f}"}),
                            width="stretch",
                            hide_index=True,
                        )
                        portfolio_report_lines = [
                            "Investment Recommendation System - Portfolio Backtest Summary",
                            "=" * 64,
                            f"Period: {portfolio_value.index[0].date()} through {portfolio_value.index[-1].date()}",
                            f"Currency: {currency}",
                            f"Starting investment: {currency} {initial_investment:,.2f}",
                            f"Ending value: {currency} {portfolio_value.iloc[-1]:,.2f}",
                            f"Period return: {portfolio_metrics['period_return_pct']:+.2f}%",
                            f"Annualized return: {portfolio_metrics['annualized_return_pct']:+.2f}%",
                            f"Annualized volatility: {portfolio_metrics['annualized_volatility_pct']:.2f}%",
                            f"Maximum drawdown: {portfolio_metrics['max_drawdown_pct']:.2f}%",
                            "",
                            "Normalized allocations:",
                        ]
                        portfolio_report_lines.extend(
                            f"  {symbol}: {weight * 100:.2f}%"
                            for symbol, weight in normalized_weights.items()
                        )
                        portfolio_report_lines.extend(
                            [
                                "",
                                "Method: adjusted-price buy-and-hold total-return proxy without periodic rebalancing.",
                                "This is not a ledger of actual tradable shares. Fees, taxes, and FX are excluded.",
                                "Historical results do not predict future performance; this is not financial advice.",
                            ]
                        )
                        download_columns = st.columns(2)
                        download_columns[0].download_button(
                            "Download backtest values (CSV)",
                            portfolio_value.to_frame().to_csv(index_label="date").encode("utf-8"),
                            file_name="portfolio_backtest.csv",
                            mime="text/csv",
                        )
                        download_columns[1].download_button(
                            "Download portfolio summary (TXT)",
                            "\n".join(portfolio_report_lines),
                            file_name="portfolio_backtest_summary.txt",
                            mime="text/plain",
                        )

with methodology_tab:
    st.subheader("Data source, calculations, and limitations")
    st.markdown(
        """
        **Market data:** Daily price history is requested from Yahoo Finance's public chart endpoint when you submit the ticker form.
        The provider is unofficial, may delay, change, rate-limit, or block requests, and may not return every symbol or date.
        Results are cached in memory by the running app for 15 minutes. A failed symbol is reported; no synthetic prices are
        substituted when a provider request fails.

        **Ticker format:** US examples include `AAPL`, `MSFT`, and `^GSPC`. NSE listings use Yahoo suffixes such as `INFY.NS`,
        `TCS.NS`, `HDFCBANK.NS`, and `^NSEI`.

        **Performance measures:** Adjusted closes include provider adjustments for distributions/splits where available.
        Period return is the first-to-last adjusted-price change. Annualized return is compounded over the observed calendar
        period. Annualized volatility uses daily return standard deviation multiplied by √252. Sharpe ratio uses a 0% risk-free
        rate. Maximum drawdown is measured against the running adjusted-price peak.

        **Buy / Hold / Sell screen:** Buy when annualized historical return is at least 8%, annualized volatility is at most 45%,
        and the latest adjusted close is at or above its available trailing 50-session average. Sell when annualized historical
        return is negative and price is below that average. All other cases are Hold. These fixed historical-momentum rules are
        simple educational heuristics, not forecasts or personalized advice.

        **Portfolio backtest:** Uses normalized starting allocations to simulate a buy-and-hold total-return portfolio from
        provider adjusted closes over the first shared history window. Provider adjustments reflect splits and distributions
        where available; this is not a ledger of tradeable shares. It requires assets quoted in one currency and does not
        periodically rebalance. It excludes fees, taxes, slippage beyond provider adjustments, currency conversion, and cash flows.
        Benchmark performance is indexed by percentage return; any cross-currency comparison excludes FX effects.

        Historical performance does not guarantee future results. This application does not execute trades or connect to a broker.
        """
    )

with privacy_tab:
    st.markdown(PRIVACY_POLICY_PATH.read_text(encoding="utf-8"))

with terms_tab:
    st.markdown(TERMS_PATH.read_text(encoding="utf-8"))

st.markdown(
    f'<footer class="app-footer">Copyright {date.today().year} Investment Recommendation System. Educational research only; not financial advice. Privacy and terms are available in the tabs above.</footer>',
    unsafe_allow_html=True,
)
