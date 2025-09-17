# Statistical Arbitrage Mean-Reversion Toolkit

This repository contains a minimal yet extensible Python implementation of a
statistical arbitrage pipeline focused on pair trading and mean-reversion. It
fetches historical prices from the OANDA v20 REST API (using your personal API
token), normalises instruments to a common currency, estimates a hedge ratio,
validates stationarity, generates Bollinger-band trading signals, runs a simple
backtest, and visualises the results.

## Project structure

```
stat-arb-ai-analyser/
├── scripts/example.py     # End-to-end demonstration using OANDA data
└── stat_arb/              # Library package with reusable components
```

Key modules:

- `stat_arb.data_providers`: Data provider abstraction and the OANDA
  implementation.
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
pip install pandas numpy statsmodels matplotlib requests python-dotenv
```

### Windows (PowerShell)

```powershell
py -3 -m venv .venv
\.\.venv\Scripts\Activate.ps1
py -m pip install pandas numpy statsmodels matplotlib requests python-dotenv
```

> **Note**
> If PowerShell prevents the activation script from running, execute
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` once
> and then re-run the activation command.

`python-dotenv` is optional, but convenient for loading the API key from a
local `.env` file.

## Configure OANDA access

Create a personal access token from the OANDA dashboard (practice or live) and
expose it via an environment variable before running any scripts:

```bash
export OANDA_API_KEY="your-api-token"
# Optional: set the environment if you want to target live instead of practice
export OANDA_ENV="practice"
```

On Windows PowerShell use `setx` or `$env:OANDA_API_KEY="..."`. When
`python-dotenv` is installed you can instead create a `.env` file with the same
variables and they will be loaded automatically by the example script.

## Quick start (OANDA example)

With the environment variables in place, run the end-to-end example to download
two instruments from OANDA, compute the spread, evaluate stationarity, backtest
multiple Bollinger windows, and generate diagnostic plots:

```bash
python -m scripts.example EUR_USD GBP_USD --interval 1h --windows 8 40 200 --k 1.75 --fee 0.6
```

On Windows PowerShell, launch the script with `py` instead of `python`.

The script prints the aligned dataset head, hedge ratio, ADF test summary, and
backtest statistics for each window. It saves a figure combining the spread,
bands, trade markers, and equity curve to the location provided via
`--plot-path` (defaults to `example_output.png`).

Use the `--fx` option when one of the instruments trades in a different
currency than your chosen base. For example, if the second leg is quoted in EUR
but you want to analyse in USD, append `--fx TICKER=EUR_USD` to the command so
that the loader can fetch the FX series for currency conversion.

## Using the library programmatically

Below is a minimal end-to-end flow using the library components directly:

```python
from datetime import datetime, timezone

from stat_arb import (
    OandaDataProvider,
    adf_test,
    compute_spread,
    estimate_hedge_ratio,
    load_pair_data,
    run_multi_window_backtest,
)

provider = OandaDataProvider(api_key="<token>", environment="practice")

pair = load_pair_data(
    provider,
    ticker_a="EUR_USD",
    ticker_b="GBP_USD",
    start=datetime(2023, 1, 1, tzinfo=timezone.utc),
    end=datetime(2024, 1, 1, tzinfo=timezone.utc),
    interval="1h",
    base_currency="USD",
)

hedge = estimate_hedge_ratio(pair.frame["A"], pair.frame["B"])
spread = compute_spread(pair.frame["A"], pair.frame["B"], hedge.ratio, hedge.intercept)
print(adf_test(spread))
results = run_multi_window_backtest(spread, windows=[20, 60], num_std=2.0, fee=0.5)
```

The helper automatically aligns timestamps (UTC), converts currencies using the
provided FX series (if any), and returns a tidy dataframe ready for analysis.

## Extending the system

- Implement additional data sources by inheriting from `DataProvider` and
  returning `PriceData` objects.
- Add alternative hedge estimators or signal generators with additional
  modules—`load_pair_data` and the backtester expect regular pandas series so
  they compose with custom analytics easily.
- The backtest is intentionally simple; extend it with position sizing,
  slippage models, or overlapping session filters as needed.

## License

MIT
