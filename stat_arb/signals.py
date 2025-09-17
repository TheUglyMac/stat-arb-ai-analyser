"""Signal generation utilities."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd


@dataclass(slots=True)
class BollingerBands:
    """Rolling statistics of a spread series."""

    window: int
    mean: pd.Series
    upper: pd.Series
    lower: pd.Series
    std: pd.Series


def compute_bollinger_bands(
    spread: pd.Series,
    window: int,
    num_std: float,
) -> BollingerBands:
    """Compute Bollinger bands for ``spread``."""

    rolling_mean = spread.rolling(window=window, min_periods=window).mean()
    rolling_std = spread.rolling(window=window, min_periods=window).std(ddof=0)
    upper = rolling_mean + num_std * rolling_std
    lower = rolling_mean - num_std * rolling_std
    return BollingerBands(window=window, mean=rolling_mean, upper=upper, lower=lower, std=rolling_std)


def compute_multi_bollinger(
    spread: pd.Series,
    windows: Iterable[int],
    num_std: float,
) -> dict[int, BollingerBands]:
    """Compute Bollinger bands for multiple windows."""

    return {window: compute_bollinger_bands(spread, window, num_std) for window in windows}
