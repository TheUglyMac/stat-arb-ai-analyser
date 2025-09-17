# Statistical Arbitrage Mean-Reversion Toolkit

This repository contains a minimal yet extensible Python implementation of a
statistical arbitrage pipeline focused on pair trading and mean-reversion. It
can fetch market data from pluggable providers, normalise instruments to a
common currency, estimate a hedge ratio, validate stationarity, generate
Bollinger-band trading signals, run a simple backtest, and visualise the
results.

The default setup ships with a CSV-based data provider for offline
experimentation and a Yahoo Finance provider for live downloads (requires
network access). The design leaves space to plug in further providers such as
OANDA or custom APIs.

## Project structure

```
stat-arb-ai-analyser/
├── data/                  # Sample CSV data used by the example script
├── scripts/example.py     # End-to-end demonstration
└── stat_arb/              # Library package with reusable components
```

Key modules:

- `stat_arb.data_providers`: Data provider abstraction, CSV and Yahoo
  implementations.
- `stat_arb.data`: Helpers to load, align, and currency-normalise price series.
- `stat_arb.hedge`: OLS hedge ratio estimation and spread calculation.
- `stat_arb.stationarity`: Augmented Dickey-Fuller test wrapper.
- `stat_arb.signals`: Bollinger-band computation.
- `stat_arb.backtest`: Mean-reversion backtest with trade log and statistics.
- `stat_arb.plotting`: Matplotlib plots for spreads and equity curves.

## Installation

Python 3.11+ is recommended. Creating a virtual environment keeps the project
dependencies isolated from the rest of your system.

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pandas numpy statsmodels matplotlib yfinance
```

### Windows (PowerShell)

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install pandas numpy statsmodels matplotlib yfinance
```

> **Note**
> If PowerShell prevents the activation script from running, execute
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` once
> and then re-run the activation command.

The Yahoo provider imports `yfinance` lazily; install it only if you plan to
use it.

## Quick start (CSV example)

The repository includes synthetic CSV data that mimics two equities priced in
USD and EUR, plus a EURUSD FX series. Run the example script to execute the
full workflow and produce summary statistics as well as plots.

```bash
python -m scripts.example
```

On Windows, run the script with the `py` launcher instead:

```powershell
py -m scripts.example
```

This prints the aligned dataset, hedge ratio, ADF test results, and a
multi-window backtest summary. A plot combining the spread, Bollinger bands,
trade markers, and equity curve is saved to
`example_output.png` in the repository root.

## Using the library programmatically

A minimal end-to-end flow looks like this:

```python
from datetime import datetime, timezone
from stat_arb import (
    CSVDataProvider,
    load_pair_data,
    estimate_hedge_ratio,
    compute_spread,
    adf_test,
    run_multi_window_backtest,
)

provider = CSVDataProvider({
    "SPY": {"path": "spy.csv", "currency": "USD"},
    "DAX": {"path": "dax.csv", "currency": "EUR"},
    "EURUSD": {"path": "eurusd.csv", "currency": "USD"},
})

pair = load_pair_data(
    provider,
    ticker_a="SPY",
    ticker_b="DAX",
    start=datetime(2023, 1, 1, tzinfo=timezone.utc),
    end=datetime(2024, 1, 1, tzinfo=timezone.utc),
    interval="1D",
    base_currency="USD",
    fx_tickers={"DAX": "EURUSD"},
)

hedge = estimate_hedge_ratio(pair.frame["A"], pair.frame["B"])
spread = compute_spread(pair.frame["A"], pair.frame["B"], hedge.ratio, hedge.intercept)
print(adf_test(spread))
results = run_multi_window_backtest(spread, windows=[20, 60], num_std=2.0, fee=0.5)
```

Swap in `YahooFinanceDataProvider` when live data is required:

```python
from stat_arb import YahooFinanceDataProvider

provider = YahooFinanceDataProvider()
pair = load_pair_data(
    provider,
    ticker_a="TM",  # Toyota Motors
    ticker_b="VOW3.DE",  # Volkswagen (EUR)
    start=datetime(2023, 1, 1, tzinfo=timezone.utc),
    end=datetime(2025, 1, 1, tzinfo=timezone.utc),
    interval="1d",
    base_currency="USD",
    fx_tickers={"VOW3.DE": "EURUSD=X"},
)
```

The helper automatically aligns timestamps (UTC), converts currencies using the
provided FX series, and returns a tidy dataframe ready for analysis.

## Extending the system

- Implement new providers by inheriting from `DataProvider` and returning
  `PriceData` objects.
- Add alternative hedge estimators or signal generators with additional
  modules—`load_pair_data` and the backtester expect regular pandas series so
  they compose with custom analytics easily.
- The backtest is intentionally simple; extend it with position sizing,
  slippage models, or overlapping session filters as needed.

## License

MIT
