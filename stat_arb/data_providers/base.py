"""Base classes and helpers for data providers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

import pandas as pd


@dataclass(slots=True)
class PriceData:
    """Container for price series returned by a data provider.

    Attributes:
        prices: Time-indexed series of prices.
        currency: ISO currency code for the price series.
    """

    prices: pd.Series
    currency: str

    def __post_init__(self) -> None:
        if not isinstance(self.prices.index, pd.DatetimeIndex):
            raise TypeError("Price series must be indexed by a DatetimeIndex")
        if not self.prices.index.is_monotonic_increasing:
            self.prices = self.prices.sort_index()
        if self.prices.index.tz is None:
            self.prices.index = self.prices.index.tz_localize("UTC")
        else:
            self.prices.index = self.prices.index.tz_convert("UTC")
        self.currency = self.currency.upper()


class DataProvider(ABC):
    """Abstract data provider capable of returning historical price data."""

    @abstractmethod
    def fetch(
        self,
        ticker: str,
        start: datetime,
        end: datetime,
        interval: str,
    ) -> PriceData:
        """Fetch historical prices for ``ticker`` between ``start`` and ``end``."""


class SupportsFetch(Protocol):
    """Protocol used for typing alternative FX providers."""

    def fetch(
        self,
        ticker: str,
        start: datetime,
        end: datetime,
        interval: str,
    ) -> PriceData:
        """Fetch price data for ``ticker``."""
