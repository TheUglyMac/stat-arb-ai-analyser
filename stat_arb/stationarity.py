"""Stationarity diagnostics for spread series."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from statsmodels.tsa.stattools import adfuller


@dataclass(slots=True)
class ADFResult:
    """Summary of the augmented Dickey-Fuller test."""

    statistic: float
    p_value: float
    lags: int
    nobs: int
    critical_values: dict[str, float]
    ic_best: float | None


def adf_test(series: pd.Series) -> ADFResult:
    """Run an augmented Dickey-Fuller test on ``series``."""

    clean = series.dropna()
    result = adfuller(clean)
    statistic, p_value, lags, nobs, critical_values, ic_best = result
    return ADFResult(
        statistic=float(statistic),
        p_value=float(p_value),
        lags=int(lags),
        nobs=int(nobs),
        critical_values={k: float(v) for k, v in critical_values.items()},
        ic_best=float(ic_best) if ic_best is not None else None,
    )
