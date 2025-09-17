"""Data loading utilities for the stat arb workflow."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from .data_providers.base import DataProvider, SupportsFetch


@dataclass(slots=True)
class PairData:
    """Aligned price history for the two legs of a spread."""

    frame: pd.DataFrame
    currency_a: str
    currency_b: str


def _ensure_series(series: pd.Series, name: str) -> pd.Series:
    if not isinstance(series.index, pd.DatetimeIndex):
        raise TypeError(f"Series {name!r} must be indexed by datetime")
    series = series.sort_index()
    if series.index.tz is None:
        series.index = series.index.tz_localize("UTC")
    else:
        series.index = series.index.tz_convert("UTC")
    series.name = name
    return series


def _parse_fx_pair(ticker: str) -> tuple[str, str]:
    letters = "".join(ch for ch in ticker if ch.isalpha())
    if len(letters) != 6:
        raise ValueError(
            f"Unable to infer FX pair structure from ticker {ticker!r}. Provide a 6-letter pair"
        )
    return letters[:3].upper(), letters[3:6].upper()


def _convert_currency(
    prices: pd.Series,
    source_currency: str,
    base_currency: str,
    fx_pair: str,
    fx_series: pd.Series,
) -> pd.Series:
    source_currency = source_currency.upper()
    base_currency = base_currency.upper()
    fx_base, fx_quote = _parse_fx_pair(fx_pair)
    if source_currency == base_currency:
        return prices

    if source_currency == fx_base and base_currency == fx_quote:
        converted = prices * fx_series
    elif source_currency == fx_quote and base_currency == fx_base:
        converted = prices / fx_series
    else:
        raise ValueError(
            f"FX ticker {fx_pair!r} is incompatible with conversion from "
            f"{source_currency} to {base_currency}."
        )
    converted.name = prices.name
    return converted


def _resolve_fx_ticker(
    fx_spec: str | Mapping[str, str] | None,
    symbol: str,
) -> str | None:
    if fx_spec is None:
        return None
    if isinstance(fx_spec, str):
        return fx_spec
    return fx_spec.get(symbol)


def load_pair_data(
    provider: DataProvider,
    ticker_a: str,
    ticker_b: str,
    start: datetime,
    end: datetime,
    interval: str,
    base_currency: str = "USD",
    fx_tickers: str | Mapping[str, str] | None = None,
    fx_provider: SupportsFetch | None = None,
) -> PairData:
    """Load and align the two legs into a tidy DataFrame.

    Args:
        provider: Data provider used for the main instruments.
        ticker_a: Symbol of the first instrument.
        ticker_b: Symbol of the second instrument.
        start: Start of the analysis window.
        end: End of the analysis window.
        interval: Bar frequency understood by the provider (e.g. ``"1d"``).
        base_currency: Currency the analysis should operate in.
        fx_tickers: Optional FX ticker or mapping per symbol, required when the
            instrument currency differs from the base currency.
        fx_provider: Optional provider to load FX data from; defaults to
            ``provider`` when omitted.
    """

    fx_provider = fx_provider or provider

    data_a = provider.fetch(ticker_a, start, end, interval)
    data_b = provider.fetch(ticker_b, start, end, interval)

    series_dict: dict[str, pd.Series] = {
        "A": _ensure_series(data_a.prices, "A"),
        "B": _ensure_series(data_b.prices, "B"),
    }

    fx_cache: dict[str, pd.Series] = {}

    for ticker, price_data, column in (
        (ticker_a, data_a, "A"),
        (ticker_b, data_b, "B"),
    ):
        currency = price_data.currency.upper()
        if currency == base_currency.upper():
            continue
        fx_ticker = _resolve_fx_ticker(fx_tickers, ticker)
        if fx_ticker is None:
            raise ValueError(
                f"Currency for {ticker} is {currency}, but no FX ticker provided to convert to"
                f" {base_currency}. Supply fx_tickers for this instrument."
            )
        if fx_ticker not in fx_cache:
            fx_data = fx_provider.fetch(fx_ticker, start, end, interval)
            fx_cache[fx_ticker] = _ensure_series(fx_data.prices, fx_ticker)
        series_dict[f"FX_{fx_ticker}"] = fx_cache[fx_ticker]

    frame = pd.concat(series_dict.values(), axis=1, join="inner").dropna().sort_index()
    for ticker, price_data, column in (
        (ticker_a, data_a, "A"),
        (ticker_b, data_b, "B"),
    ):
        currency = price_data.currency.upper()
        if currency == base_currency.upper():
            continue
        fx_ticker = _resolve_fx_ticker(fx_tickers, ticker)
        fx_series = frame[f"FX_{fx_ticker}"]
        frame[column] = _convert_currency(frame[column], currency, base_currency, fx_ticker, fx_series)

    fx_columns = [col for col in frame.columns if col.startswith("FX_")]
    frame = frame.drop(columns=fx_columns)
    frame.index.name = "timestamp"
    return PairData(frame=frame, currency_a=data_a.currency, currency_b=data_b.currency)
