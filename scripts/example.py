"""Example end-to-end workflow using the OANDA data provider."""
from __future__ import annotations

import argparse
import logging
import os
from datetime import datetime, timedelta, timezone

import matplotlib.pyplot as plt

try:  # Optional dependency, only needed for local development convenience
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional helper
    load_dotenv = None  # type: ignore[assignment]

from stat_arb import (
    OandaDataProvider,
    adf_test,
    compute_spread,
    estimate_hedge_ratio,
    load_pair_data,
    plot_equity_curve,
    plot_spread_with_bands,
    run_multi_window_backtest,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def _parse_datetime(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _parse_kv_pairs(values: list[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for entry in values:
        if "=" not in entry:
            raise ValueError(f"Expected key=value mapping, got {entry!r}")
        key, val = entry.split("=", 1)
        mapping[key.strip()] = val.strip()
    return mapping


def _default_start_end() -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=180)
    return start, now


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a stat arb backtest using OANDA data.")
    parser.add_argument("ticker_a", help="First instrument symbol (e.g. EUR_USD)")
    parser.add_argument("ticker_b", help="Second instrument symbol (e.g. GBP_USD)")
    parser.add_argument(
        "--start",
        type=_parse_datetime,
        help="Inclusive start timestamp (ISO 8601, default: 180 days ago)",
    )
    parser.add_argument(
        "--end",
        type=_parse_datetime,
        help="Exclusive end timestamp (ISO 8601, default: now)",
    )
    parser.add_argument(
        "--interval",
        default="1h",
        help="Bar interval (e.g. 1m, 5m, 1h, 1d). See OANDA granularity docs for supported values.",
    )
    parser.add_argument(
        "--base-currency",
        default="USD",
        help="Target currency for analysis (default: USD)",
    )
    parser.add_argument(
        "--fx",
        action="append",
        default=[],
        help="Optional currency conversion mapping in the form SYMBOL=FX_PAIR. Repeatable.",
    )
    parser.add_argument(
        "--windows",
        type=int,
        nargs="+",
        default=[10, 20, 40],
        help="Lookback windows for Bollinger bands (default: 10 20 40)",
    )
    parser.add_argument(
        "--k",
        type=float,
        default=1.5,
        help="Number of standard deviations for the Bollinger bands (default: 1.5)",
    )
    parser.add_argument(
        "--fee",
        type=float,
        default=0.1,
        help="Per-trade transaction cost deducted in spread units (default: 0.1)",
    )
    parser.add_argument(
        "--environment",
        choices=["practice", "live"],
        default=os.environ.get("OANDA_ENV", "practice"),
        help="OANDA environment to use (default sourced from OANDA_ENV or 'practice')",
    )
    parser.add_argument(
        "--plot-path",
        default="example_output.png",
        help="File path for the output plot (default: example_output.png)",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    if load_dotenv is not None:
        load_dotenv()

    parser = build_argument_parser()
    args = parser.parse_args(argv)

    api_key = os.environ.get("OANDA_API_KEY")
    if not api_key:
        raise RuntimeError("Set the OANDA_API_KEY environment variable before running the script.")

    start_default, end_default = _default_start_end()
    start = args.start or start_default
    end = args.end or end_default
    try:
        fx_mapping = _parse_kv_pairs(args.fx) if args.fx else None
    except ValueError as exc:
        parser.error(str(exc))

    provider = OandaDataProvider(api_key=api_key, environment=args.environment)

    pair = load_pair_data(
        provider,
        ticker_a=args.ticker_a,
        ticker_b=args.ticker_b,
        start=start,
        end=end,
        interval=args.interval,
        base_currency=args.base_currency,
        fx_tickers=fx_mapping
    )

    print("Aligned data head:")
    print(pair.frame.head())

    hedge = estimate_hedge_ratio(pair.frame["A"], pair.frame["B"])
    spread = compute_spread(pair.frame["A"], pair.frame["B"], hedge.ratio, hedge.intercept)

    print("\nHedge ratio")
    print(f"ratio={hedge.ratio:.4f}, intercept={hedge.intercept:.4f}")

    adf_result = adf_test(spread)
    print("\nADF test")
    print(f"statistic={adf_result.statistic:.4f}, p-value={adf_result.p_value:.4f}, lags={adf_result.lags}")
    print("critical values:")
    for level, value in adf_result.critical_values.items():
        print(f"  {level}: {value:.4f}")
    if adf_result.p_value > 0.05:
        print("WARNING: Spread may not be stationary at the 5% level.")

    results = run_multi_window_backtest(spread, windows=args.windows, num_std=args.k, fee=args.fee)


    print("\nBacktest summary")
    for window, result in results.items():
        stats = result.stats
        win_rate_pct = stats.win_rate * 100
        print(
            f"window={window:>3} | trades={stats.num_trades:>2} | win%={win_rate_pct:5.1f} | "
            f"avg win={stats.avg_win:.3f} | avg loss={stats.avg_loss:.3f} | "
            f"total pnl={stats.total_pnl:.3f} | sharpe={stats.sharpe:.3f} | "
            f"max drawdown={stats.max_drawdown:.3f}"
        )

    best_window = max(results.values(), key=lambda res: res.stats.total_pnl)
    print(f"\nBest window: {best_window.window} with total pnl {best_window.stats.total_pnl:.3f}")

    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    plot_spread_with_bands(spread, best_window.bands, best_window.trades, ax=axes[0])
    plot_equity_curve(best_window.equity_curve, ax=axes[1])
    plt.tight_layout()
    fig.savefig(args.plot_path, dpi=150)
    print(f"Saved plot to {args.plot_path}")


if __name__ == "__main__":
    main()
