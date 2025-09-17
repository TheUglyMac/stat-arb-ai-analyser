"""Hedge ratio estimation utilities."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import statsmodels.api as sm


@dataclass(slots=True)
class HedgeRatioResult:
    """OLS hedge ratio estimation result."""

    ratio: float
    intercept: float
    model_summary: str


def estimate_hedge_ratio(
    series_a: pd.Series,
    series_b: pd.Series,
    add_intercept: bool = False,
) -> HedgeRatioResult:
    """Estimate the hedge ratio of ``series_a`` relative to ``series_b``.

    Args:
        series_a: Price series of the first leg.
        series_b: Price series of the second leg.
        add_intercept: When ``True`` includes an intercept term in the regression.

    Returns:
        :class:`HedgeRatioResult` describing the slope and intercept.
    """

    aligned = pd.concat([series_a, series_b], axis=1, join="inner").dropna()
    y = aligned.iloc[:, 0].astype(float)
    x = aligned.iloc[:, 1].astype(float)

    exog = x.values.reshape(-1, 1)
    if add_intercept:
        X = sm.add_constant(exog)
        model = sm.OLS(y.values, X).fit()
        intercept = float(model.params[0])
        ratio = float(model.params[1])
    else:
        model = sm.OLS(y.values, exog).fit()
        intercept = 0.0
        ratio = float(model.params[0])

    return HedgeRatioResult(ratio=ratio, intercept=intercept, model_summary=str(model.summary()))


def compute_spread(
    series_a: pd.Series,
    series_b: pd.Series,
    hedge_ratio: float,
    intercept: float = 0.0,
) -> pd.Series:
    """Compute the spread between two series using ``hedge_ratio``."""

    spread = series_a - (hedge_ratio * series_b + intercept)
    spread.name = "spread"
    return spread
