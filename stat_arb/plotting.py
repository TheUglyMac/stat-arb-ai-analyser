"""Plotting helpers for quick diagnostics."""
from __future__ import annotations

from typing import Iterable

import matplotlib.pyplot as plt
import pandas as pd

from .backtest import Trade
from .signals import BollingerBands


def plot_spread_with_bands(
    spread: pd.Series,
    bands: BollingerBands | None = None,
    trades: Iterable[Trade] | None = None,
    ax: plt.Axes | None = None,
) -> plt.Axes:
    """Plot the spread along with its Bollinger bands."""

    if ax is None:
        _, ax = plt.subplots(figsize=(12, 5))

    ax.plot(spread.index, spread, label="Spread", color="tab:blue")
    if bands is not None:
        ax.plot(bands.mean.index, bands.mean, label="Rolling mean", color="tab:orange")
        ax.plot(bands.upper.index, bands.upper, label="Upper band", color="tab:green", linestyle="--")
        ax.plot(bands.lower.index, bands.lower, label="Lower band", color="tab:red", linestyle="--")

    if trades:
        entry_label_used = False
        exit_label_used = False
        for trade in trades:
            color = "green" if trade.side == "long" else "red"
            marker = "^" if trade.side == "long" else "v"
            entry_label = "Entry" if not entry_label_used else None
            exit_label = "Exit" if not exit_label_used else None
            ax.scatter(trade.entry_time, trade.entry_spread, marker=marker, color=color, s=70, label=entry_label)
            ax.scatter(
                trade.exit_time,
                trade.exit_spread,
                marker="o",
                facecolors="none",
                edgecolors=color,
                s=70,
                label=exit_label,
            )
            entry_label_used = True
            exit_label_used = True

    ax.set_title("Spread and Bollinger Bands")
    ax.set_ylabel("Spread")
    ax.legend(loc="best")
    return ax


def plot_equity_curve(
    equity_curve: pd.Series,
    ax: plt.Axes | None = None,
) -> plt.Axes:
    """Plot the cumulative P&L over time."""

    if ax is None:
        _, ax = plt.subplots(figsize=(12, 3))
    ax.plot(equity_curve.index, equity_curve, color="tab:purple")
    ax.set_title("Equity Curve")
    ax.set_ylabel("P&L")
    ax.axhline(0, color="black", linewidth=0.8, linestyle=":")
    return ax
