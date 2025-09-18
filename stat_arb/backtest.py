"""Backtesting utilities for mean-reversion strategies."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd

from .signals import BollingerBands, compute_bollinger_bands


@dataclass(slots=True)
class Trade:
    """Representation of a completed trade."""

    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    side: str
    entry_spread: float
    exit_spread: float
    pnl: float
    fee: float


@dataclass(slots=True)
class BacktestStats:
    """High-level statistics of a backtest run."""

    num_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    total_pnl: float
    sharpe: float
    max_drawdown: float


@dataclass(slots=True)
class BacktestResult:
    """Full backtest outcome including trade log and equity curve."""

    window: int
    bands: BollingerBands
    trades: list[Trade]
    equity_curve: pd.Series
    stats: BacktestStats


def _compute_stats(equity_curve: pd.Series, trades: list[Trade]) -> BacktestStats:
    total_pnl = float(sum(trade.pnl for trade in trades))
    wins = [trade.pnl for trade in trades if trade.pnl > 0]
    losses = [trade.pnl for trade in trades if trade.pnl < 0]
    num_trades = len(trades)
    win_rate = len(wins) / num_trades if num_trades else 0.0
    avg_win = float(np.mean(wins)) if wins else 0.0
    avg_loss = float(np.mean(losses)) if losses else 0.0
    returns = equity_curve.diff().dropna()
    if not returns.empty and returns.std(ddof=0) != 0:
        sharpe = float(returns.mean() / returns.std(ddof=0))
    else:
        sharpe = 0.0
    running_max = equity_curve.cummax()
    drawdowns = equity_curve - running_max
    max_drawdown = float(drawdowns.min()) if not drawdowns.empty else 0.0
    return BacktestStats(
        num_trades=num_trades,
        win_rate=win_rate,
        avg_win=avg_win,
        avg_loss=avg_loss,
        total_pnl=total_pnl,
        sharpe=sharpe,
        max_drawdown=max_drawdown,
    )


def backtest_bollinger(
    spread: pd.Series,
    window: int,
    num_std: float,
    fee: float = 0.0,
) -> BacktestResult:
    """Run a Bollinger-band mean reversion backtest on ``spread``."""

    bands = compute_bollinger_bands(spread, window=window, num_std=num_std)
    trades: list[Trade] = []
    equity = 0.0
    equity_values: list[float] = []
    position = 0  # 0 = flat, 1 = long spread, -1 = short spread
    entry_price = 0.0
    entry_time: pd.Timestamp | None = None

    for timestamp, value in spread.items():
        mean = bands.mean.loc[timestamp]
        upper = bands.upper.loc[timestamp]
        lower = bands.lower.loc[timestamp]

        if pd.isna(mean) or pd.isna(upper) or pd.isna(lower):
            equity_values.append(equity)
            continue

        if position == 0:
            if value <= lower:
                position = 1
                entry_price = float(value)
                entry_time = timestamp
            elif value >= upper:
                position = -1
                entry_price = float(value)
                entry_time = timestamp
        elif position == 1:
            if value >= mean:
                pnl = float(value - entry_price - fee)
                equity += pnl
                trades.append(
                    Trade(
                        entry_time=entry_time,
                        exit_time=timestamp,
                        side="long",
                        entry_spread=float(entry_price),
                        exit_spread=float(value),
                        pnl=pnl,
                        fee=fee,
                    )
                )
                position = 0
                entry_time = None
        elif position == -1:
            if value <= mean:
                pnl = float(entry_price - value - fee)
                equity += pnl
                trades.append(
                    Trade(
                        entry_time=entry_time,
                        exit_time=timestamp,
                        side="short",
                        entry_spread=float(entry_price),
                        exit_spread=float(value),
                        pnl=pnl,
                        fee=fee,
                    )
                )
                position = 0
                entry_time = None

        equity_values.append(equity)

    equity_curve = pd.Series(equity_values, index=spread.index, name="equity")
    stats = _compute_stats(equity_curve, trades)
    return BacktestResult(
        window=window,
        bands=bands,
        trades=trades,
        equity_curve=equity_curve,
        stats=stats,
    )


def run_multi_window_backtest(
    spread: pd.Series,
    windows: Iterable[int],
    num_std: float,
    fee: float = 0.0,
) -> dict[int, BacktestResult]:
    """Run Bollinger backtests for several lookback windows."""

    results: dict[int, BacktestResult] = {}
    for window in windows:
        results[window] = backtest_bollinger(spread, window=window, num_std=num_std, fee=fee)
    return results
