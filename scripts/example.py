"""Example end-to-end workflow using the CSV data provider."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import matplotlib.pyplot as plt

from stat_arb import (
    CSVDataProvider,
    load_pair_data,
    estimate_hedge_ratio,
    compute_spread,
    adf_test,
    run_multi_window_backtest,
    plot_spread_with_bands,
    plot_equity_curve,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def main() -> None:
    provider = CSVDataProvider(
        {
            "A": {
                "path": "data/sample_A.csv",
                "currency": "USD",
            },
            "B": {
                "path": "data/sample_B.csv",
                "currency": "EUR",
            },
            "EURUSD": {
                "path": "data/sample_EURUSD.csv",
                "currency": "USD",
            },
        }
    )

    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = datetime(2024, 6, 28, tzinfo=timezone.utc)
    pair = load_pair_data(
        provider,
        ticker_a="A",
        ticker_b="B",
        start=start,
        end=end,
        interval="1D",
        base_currency="USD",
        fx_tickers={"B": "EURUSD"},
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

    windows = [10, 20, 40]
    k = 1.5
    fee = 0.1
    results = run_multi_window_backtest(spread, windows=windows, num_std=k, fee=fee)

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
    output_path = "example_output.png"
    fig.savefig(output_path, dpi=150)
    print(f"Saved plot to {output_path}")


if __name__ == "__main__":
    main()
